import pandas as pd
import pymongo
import warnings
import ast
import streamlit as st
import re
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

warnings.filterwarnings('ignore')

# Function to fetch MongoDB collection as a DataFrame
def fetch_collection_as_df(collection_name, db):
    try:
        collection = db[collection_name]
        df = pd.DataFrame(list(collection.find()))
        if '_id' in df.columns:
            df = df.drop('_id', axis=1)  # Drop MongoDB's default `_id` column for simplicity
        return df
    except Exception as e:
        st.error(f"Error fetching data from collection '{collection_name}': {e}")
        return pd.DataFrame()

# Main dashboard function
def dashboard_page(database):
    # Fetch collections as DataFrames
    articles_df = fetch_collection_as_df('articles', database)
    careers_df = fetch_collection_as_df('careers', database)
    teams_df = fetch_collection_as_df('teams', database)
    practices_df = fetch_collection_as_df('practices', database)


    core_roles = sorted([
        'Founding Partner', 'Managing Partner', 'Partner', 'Associate', 'Of Counsel',
        'Senior Associate', 'Counsel', 'Law Clerk', 'Paralegal', 'Patent Agent',
        'Chief Executive Officer', 'Chief Operating Officer', 'Chief Financial Officer',
        'Chief Marketing Officer', 'Chief Information Officer', 'Chief People Officer',
        'Director', 'Manager', 'Chairman', 'Consultant', 'Accountant', 'Clerk',
        'Attorney', 'Advisor', 'Specialist', 'Nurse', 'Engineer', 'Assistant',
        'Administrator', 'Retired', 'In Memoriam', 'Member', 'General Counsel'
    ], key=len, reverse=True)

    def extract_role(position):
        if pd.isna(position):
            return 'Other'
        position = str(position).title().strip()
        for role in core_roles:
            if role in position:
                return role
        return 'Other'

    teams_df['Core_Role'] = teams_df.get('position', '').apply(extract_role)

    # Standardize Location
    def standardize_location(location):
        if isinstance(location, str):
            return location.split(',')[0].strip()
        return 'Unknown'

    careers_df['City'] = careers_df.get('location', '').apply(standardize_location)

    # Extract Position Type
    def extract_position_type(position):
        position = str(position).lower()
        if 'paralegal' in position:
            return 'Paralegal'
        elif any(keyword in position for keyword in ['attorney', 'litigation', 'counsel']):
            return 'Attorney'
        elif 'associate' in position and 'attorney' not in position:
            return 'Associate'
        elif 'partner' in position:
            return 'Partner'
        elif any(keyword in position for keyword in ['director', 'manager']):
            return 'Manager/Director'
        elif 'assistant' in position:
            return 'Assistant'
        elif 'clerk' in position:
            return 'Clerk'
        elif any(keyword in position for keyword in ['technician', 'specialist']):
            return 'Technician/Specialist'
        elif 'coordinator' in position:
            return 'Coordinator'
        elif any(keyword in position for keyword in ['billing', 'accountant']):
            return 'Finance/Accounting'
        elif any(keyword in position for keyword in ['human resources', 'hr']):
            return 'Human Resources'
        elif any(keyword in position for keyword in ['marketing', 'business development']):
            return 'Marketing/Business Development'
        elif any(keyword in position for keyword in ['externship', 'talent pool']):
            return 'Internship/Externship'
        return 'Other'

    careers_df['Position_Type'] = careers_df.get('position', '').apply(extract_position_type)

    # Alumni Extraction
    def extract_alumni(education):
        if pd.isna(education):
            return ['Unknown']
        matches = re.findall(r"'([^']+)'", education)
        universities = [match.split(',')[0].strip() for match in matches]
        valid_universities = [
            uni for uni in universities if
            re.search(r'\b(University|College|School|Institute)\b', uni, re.IGNORECASE)
        ]
        return valid_universities if valid_universities else ['Unknown']

    teams_df['education_cleaned'] = teams_df.get('education', '').apply(extract_alumni)
    education_expanded = teams_df.explode('education_cleaned')
    education_expanded = education_expanded[education_expanded['education_cleaned'] != 'Unknown']

    # Normalize Institution Names
    normalization_map = {
        'University at Buffalo School of Law': 'University at Buffalo',
        'State University of New York at Buffalo Law School': 'University at Buffalo',
        'Cornell Law School': 'Cornell University',
        'Georgetown University Law Center': 'Georgetown University',
    }
    education_expanded['education_cleaned'] = education_expanded['education_cleaned'].replace(normalization_map)

    # Aggregate Top Education Institutions
    top_education_counts = (
        education_expanded
        .groupby(['education_cleaned', 'firm'])
        .size()
        .reset_index(name='Count')
    )
    top_institutions = top_education_counts.groupby('education_cleaned')['Count'].sum().nlargest(10).index
    top_education_counts = top_education_counts[top_education_counts['education_cleaned'].isin(top_institutions)]

    # Count Awards and Affiliations
    def parse_and_count(field):
        try:
            field_list = ast.literal_eval(field)
            return len(field_list) if isinstance(field_list, list) else 0
        except (ValueError, SyntaxError):
            return 0

    teams_df['award_count'] = teams_df.get('achievements', '').apply(parse_and_count)
    teams_df['affiliation_count'] = teams_df.get('affiliations', '').apply(parse_and_count)

    # Aggregate Lawyer Awards and Affiliations
    lawyer_awards = (
        teams_df.groupby(['name', 'firm'])['award_count']
        .sum()
        .reset_index()
        .sort_values(by='award_count', ascending=False)
    )

    lawyer_affiliations = (
        teams_df.groupby(['name', 'firm'])['affiliation_count']
        .sum()
        .reset_index()
        .sort_values(by='affiliation_count', ascending=False)
    )


    # ------------------------------------- Dashboard UI --------------------------------------------- #

    # ------------------------------------- Dashboard --------------------------------------------- #
    # Set up full-width layout and global dropdown
    st.title("Integrated Legal Analytics Dashboard")

    # Dropdown at the top-right
    col_top = st.columns(
        [8, 2])  # Allocate most of the space to the left and leave a small space for the dropdown on the right
    with col_top[1]:  # Right-most column
        firm_options = ['Overall'] + sorted(teams_df['firm'].unique()) if 'firm' in teams_df else ['Overall']
        selected_firm = st.selectbox("Select a Firm", firm_options, key="firm_dropdown")

    # Container for the first row of plots: Sunburst and Educational Institutions
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        sunburst_data = teams_df.groupby(['firm', 'Core_Role']).size().reset_index(name='Count')
        sunburst_fig = px.sunburst(
            sunburst_data,
            path=['firm', 'Core_Role'],
            values='Count',
            title="Team Member Distribution Across Firm",
            height=600,
            width=500
        )
        sunburst_fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percentParent:.2%}",
            textinfo='label+value',  # Show labels and percentages
        )
        st.plotly_chart(sunburst_fig, use_container_width=True)

    with row1_col2:
        traces = []
        custom_colors = px.colors.qualitative.Bold
        for idx, firm in enumerate(top_education_counts['firm'].unique()):
            firm_data = top_education_counts[top_education_counts['firm'] == firm]
            traces.append(
                go.Bar(
                    x=firm_data['Count'],
                    y=firm_data['education_cleaned'],
                    name=firm,
                    orientation='h',
                    marker=dict(color=custom_colors[idx % len(custom_colors)])
                )
            )
        education_fig = go.Figure(data=traces)
        education_fig.update_layout(
            title="Top 10 Alumni Institutions by Recruitment",
            barmode='stack',
            xaxis=dict(title="Number of Alumni"),
            yaxis=dict(title="Educational Institution", categoryorder='total ascending'),
            height=600,
            width=400
        )
        st.plotly_chart(education_fig, use_container_width=True)

    # Container for the second row: Heatmap, Awards, Affiliations
    row2_col1, row2_col2, row2_col3 = st.columns([2, 1, 1])

    with row2_col1:
        positions_by_city_firm = careers_df.groupby(['City', 'firm']).size().unstack(fill_value=0)
        heatmap_fig = go.Figure(data=go.Heatmap(
            z=positions_by_city_firm.values,
            x=positions_by_city_firm.columns,
            y=positions_by_city_firm.index,
            colorscale='Darkmint',
            showscale=True
        ))
        heatmap_fig.update_layout(
            title="Job Openings by City and Firm",
            xaxis=dict(title="Firm"),
            yaxis=dict(title="City"),
            margin=dict(t=50, l=80, b=50, r=20)
        )

        annotations = []
        for i, city in enumerate(positions_by_city_firm.index):
            for j, firm in enumerate(positions_by_city_firm.columns):
                value = positions_by_city_firm.iloc[i, j]
                annotations.append(dict(
                    x=firm,
                    y=city,
                    text=str(value),
                    showarrow=False,
                    font=dict(color='white' if value > positions_by_city_firm.values.max() / 2 else 'black')
                ))

        heatmap_fig.update_layout(annotations=annotations)
        st.plotly_chart(heatmap_fig, use_container_width=True)

    with row2_col2:
        if selected_firm == "Overall":
            filtered_awards = lawyer_awards.groupby('name', as_index=False).agg({'award_count': 'sum', 'firm': 'first'})
        else:
            filtered_awards = lawyer_awards[lawyer_awards['firm'] == selected_firm]
        filtered_awards = filtered_awards.nlargest(10, 'award_count')
        awards_fig = go.Figure(data=[
            go.Bar(
                x=filtered_awards['award_count'],
                y=filtered_awards['name'],
                orientation='h',
                marker=dict(color='steelblue')
            )
        ])
        awards_fig.update_layout(
            title="Top 10 Individuals by Awards",
            xaxis_title="Number of Awards",
            yaxis_title="Lawyer",
            yaxis=dict(categoryorder='total ascending'),
            height=500
        )
        st.plotly_chart(awards_fig, use_container_width=True)

    with row2_col3:
        if selected_firm == "Overall":
            filtered_affiliations = lawyer_affiliations.groupby('name', as_index=False).agg(
                {'affiliation_count': 'sum', 'firm': 'first'})
        else:
            filtered_affiliations = lawyer_affiliations[lawyer_affiliations['firm'] == selected_firm]
        filtered_affiliations = filtered_affiliations.nlargest(10, 'affiliation_count')
        affiliations_fig = go.Figure(data=[
            go.Bar(
                x=filtered_affiliations['affiliation_count'],
                y=filtered_affiliations['name'],
                orientation='h',
                marker=dict(color='mediumseagreen')
            )
        ])
        affiliations_fig.update_layout(
            title="Top 10 Individuals by Affiliations",
            xaxis_title="Number of Affiliations",
            yaxis_title="Lawyer",
            yaxis=dict(categoryorder='total ascending'),
            height=500
        )
        st.plotly_chart(affiliations_fig, use_container_width=True)

    # Container for the third row: Articles, Sunburst, and Pie Chart
    row3_col1, row3_col2, row3_col3 = st.columns([2, 2, 2])

    with row3_col1:
        firm_area_counts = articles_df.groupby(['firm', 'area']).size().reset_index(name='Article_Count')
        firm_totals = firm_area_counts.groupby('firm')['Article_Count'].sum().reset_index()
        firm_totals = firm_totals.sort_values(by='Article_Count', ascending=False)
        firm_area_counts['firm'] = pd.Categorical(firm_area_counts['firm'], categories=firm_totals['firm'],
                                                  ordered=True)
        firm_area_counts = firm_area_counts.sort_values(by=['firm', 'Article_Count'], ascending=[True, False])
        color_palette = px.colors.qualitative.Set3
        areas = firm_area_counts['area'].unique()
        traces = []
        for i, area in enumerate(areas):
            area_data = firm_area_counts[firm_area_counts['area'] == area]
            traces.append(go.Bar(
                x=area_data['firm'],
                y=area_data['Article_Count'],
                name=area,
                text=area_data['Article_Count'],
                textposition='inside',
                marker=dict(color=color_palette[i % len(color_palette)])
            ))
        articles_fig = go.Figure(data=traces)
        articles_fig.update_layout(
            title="Articles and Blogs Coverage by Firms",
            xaxis=dict(title="Firm", tickangle=-30),
            yaxis=dict(title="Number of Articles"),
            barmode='stack',
            height=500
        )
        st.plotly_chart(articles_fig, use_container_width=True)

    with row3_col2:
        practices_df['team_members_count'] = practices_df['team members'].apply(
            lambda x: len(eval(x)) if pd.notnull(x) else 0
        )
        team_members_sunburst = practices_df.groupby(['firm', 'standardized_title'], as_index=False).agg(
            {'team_members_count': 'sum'}
        )
        if selected_firm != "Overall":
            team_members_sunburst = team_members_sunburst[team_members_sunburst['firm'] == selected_firm]
        sunburst_fig = px.sunburst(
            team_members_sunburst,
            path=['firm', 'standardized_title'],
            values='team_members_count',
            title="Team Member Distribution by Practice Areas",
            height=500
        )
        sunburst_fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percentParent:.2%}",
            textinfo='label+value'
        )
        st.plotly_chart(sunburst_fig, use_container_width=True)

    with row3_col3:
        # Apply the firm filter to the careers DataFrame
        if selected_firm != "Overall":
            filtered_careers_df = careers_df[careers_df['firm'] == selected_firm]
        else:
            filtered_careers_df = careers_df

        # Group the filtered data by Position_Type
        filtered_data = filtered_careers_df.groupby('Position_Type').size().reset_index(name='Count')

        # Create the pie chart
        pie_fig = px.pie(
            filtered_data,
            values='Count',
            names='Position_Type',
            title=f"Job Positions by Type ({selected_firm})" if selected_firm != "Overall" else "Job Positions by Type (All Firms)",
            color_discrete_sequence=px.colors.qualitative.Bold
        )

        # Highlight the largest segment
        pie_fig.update_traces(
            textinfo='label+percent',
            pull=[0.1 if i == filtered_data['Count'].idxmax() else 0 for i in range(len(filtered_data))]
        )

        # Display the pie chart
        st.plotly_chart(pie_fig, use_container_width=True)


    # Container for the fourth row: Practice Area Bar Chart, Word Cloud, and Searchable Dataframe
    row4_col1, row4_col2, row4_col3 = st.columns([1, 2, 2])

    # Practice Area Bar Chart in col1
    with row4_col1:
        practice_area_count = practices_df.groupby('firm').size().reset_index(name='Number of Practice Areas')
        practice_area_count_sorted = practice_area_count.sort_values(by='Number of Practice Areas', ascending=False)
        colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880']
        practice_area_fig = go.Figure(
            data=[
                go.Bar(
                    x=practice_area_count_sorted['firm'],
                    y=practice_area_count_sorted['Number of Practice Areas'],
                    text=practice_area_count_sorted['Number of Practice Areas'],
                    textposition='auto',
                    marker=dict(color=colors[:len(practice_area_count_sorted)])
                )
            ]
        )
        practice_area_fig.update_layout(
            title="Unique Practice Areas by Firm",
            xaxis=dict(title="Firm"),
            yaxis=dict(title="Number of Practice Areas"),
            template="plotly_white",
            margin=dict(t=50, l=50, b=50, r=50),
            height=400,
            width=500
        )
        st.plotly_chart(practice_area_fig, use_container_width=True)

    # Treemap in col2
    with row4_col2:
        # Prepare Data for Treemap
        treemap_data = careers_df.groupby(['firm', 'City', 'Position_Type']).size().reset_index(name='Count')

        # Filter Treemap Data Based on the Global Dropdown
        if selected_firm == "Overall":
            filtered_treemap_data = treemap_data.groupby(['City', 'Position_Type']).sum().reset_index()
        else:
            filtered_treemap_data = treemap_data[treemap_data['firm'] == selected_firm]

        # Create Treemap
        treemap_fig = px.treemap(
            filtered_treemap_data,
            path=['City', 'Position_Type'],  # Hierarchical structure: City > Position_Type
            values='Count',
            color='Position_Type',  # Use Position_Type to assign distinct colors
            color_discrete_sequence=px.colors.diverging.Geyser,  # Distinct color palette
            title=f"Position Types Across Cities and Firms"
        )

        # Customize Treemap Layout
        treemap_fig.update_layout(
            margin=dict(t=50, l=25, r=25, b=25)
        )

        # Display the Treemap
        st.plotly_chart(treemap_fig, use_container_width=True)

    # Word Cloud in col3
    with row4_col3:
        # Add a professional title for the Word Cloud
        st.subheader("Specializations Word Cloud")

        # Combine all specializations into a single string
        specializations_list = practices_df['specializations'].dropna().apply(ast.literal_eval).explode()
        specializations_text = ' '.join(specializations_list)

        # Define custom stopwords (add more as needed)
        custom_stopwords = set(STOPWORDS).union(
            {'act', 'law', 'case', 'analysis', 'document', 'discovery', 'including', 'represented'})

        # Clean the text to remove common and irrelevant words
        cleaned_text = ' '.join(
            word for word in re.split(r'\W+', specializations_text.lower())
            if word not in custom_stopwords and len(word) > 2
        )

        # Generate the Word Cloud
        wordcloud = WordCloud(
            stopwords=custom_stopwords
        ).generate(cleaned_text)

        # Display the Word Cloud in Streamlit
        fig, ax = plt.subplots(figsize=(4.5, 4.5))  # Smaller size for compact layout
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        fig.patch.set_alpha(0)
        st.pyplot(fig, use_container_width=False)

    # Row 5: Practice Areas and Firms Offering Them
    st.markdown("### Practice Areas and Firms Offering Them")

    search_query = st.text_input("Search Practice Area", "")
    unique_practice_areas_df = practices_df[['standardized_title', 'firm']].drop_duplicates()
    unique_practice_areas_df = (
        unique_practice_areas_df.groupby('standardized_title')['firm']
        .apply(lambda x: ', '.join(sorted(x.unique())))
        .reset_index()
    )
    unique_practice_areas_df.columns = ['Practice Area', 'Offered by Firm']
    if search_query:
        filtered_practice_df = unique_practice_areas_df[
            unique_practice_areas_df['Practice Area'].str.contains(search_query, case=False, na=False)
        ]
    else:
        filtered_practice_df = unique_practice_areas_df

    # Display the searchable dataframe
    st.dataframe(filtered_practice_df, use_container_width=True)
