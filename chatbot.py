

import streamlit as st
from pymongo import MongoClient
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# MongoDB setup
mongo_url = "MONGODB URL HERE"
mongo_client = MongoClient(mongo_url)
database = mongo_client["RAG"]

# OpenAI client setup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)


def generate_query(user_query):
    prompt = """
    You are a data analyst generating MongoDB queries based on the provided schema and conversation history.
    Only use data from the schema and ensure queries are based solely on the `teams`, `careers`, `articles`, and `practices` collections, ignoring any unrelated or external context.
    Absolutely **do not reference any generic, historical, or publicly known figures or data**—only refer to data that exists in these collections.

    ### Example Queries

    Example Question: "Who are founding partners for Rupp Pfalzgraf?"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": { "position": { "$regex": "Founding Partner", "$options": "i" } },
      "projection": { "name": 1, "_id": 0 }
    }

    Example Question: "How many team members are there in total for each firm?"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": {},
      "aggregation": [
        { "$group": { "_id": "$firm", "total_members": { "$sum": 1 } } }
      ]
    }

    Example Question: "Which members hold multiple titles or positions?"
    Expected MongoDB Query:
    {
        "collection": "teams",
        "query": {
            "position": {
                "$regex": ","
            }
        },
        "projection": {
            "name": 1,
            "position": 1,
            "firm": 1, 
            "_id": 0
        }
    }
    
    Example Question: "Tell me about Tony Rupp's professional background."
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": { "name": "Tony Rupp" },
      "projection": { "about": 1, "_id": 0 }
    }
    
    Example Question: "Summarize David Pfalzgraf, Jr.'s experience."
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": { "name": "David Pfalzgraf, Jr." },
      "projection": { "achievements": 1, "admissions": 1, "_id": 0 }
    }
    
    Example Question: "What positions are currently available?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {},
      "projection": { "position": 1, "_id": 0 }
    }
    Example Question: "What are the unique firms represented in the data?"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": {},
      "aggregation": [
        {
          "$group": {
            "_id": null,
            "unique_firms": { "$addToSet": "$firm" }
          }
        }
      ]
    }
    
    Example Question: "What is Tony Rupp's educational background?"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": { "name": "Tony Rupp" },
      "projection": { "education": 1, "_id": 0 }
    }



    Example Question: "List the count partner team members by firm"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "query": {
        "position": {
          "$regex": "Partner",
          "$options": "i"
        }
      },
      "aggregation": [
        {
          "$match": {
            "position": {
              "$regex": "Partner",
              "$options": "i"
            }
          }
        },
        {
          "$group": {
            "_id": "$firm",
            "partner_count": { "$sum": 1 }
          }
        },
        {
          "$project": {
            "firm": "$_id",
            "_id": 0,
            "partner_count": 1
          }
        }
      ]
    }

    Example Question: "how many members attended University at Buffalo School of Law from each firm?"
    Expected MongoDB Query:
    {
      "collection": "teams",
      "aggregation": [
        {
          "$match": {
            "education": {
              "$regex": "University at Buffalo School of Law",
              "$options": "i"
            }
          }
        },
        {
          "$group": {
            "_id": "$firm",
            "count": {
              "$sum": 1
            }
          }
        },
        {
          "$project": {
            "firm": "$_id",
            "_id": 0,
            "count": 1
          }
        }
      ]
    }

    Example Question: "List all available positions in Buffalo, NY."
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": { "location": { "$regex": "Buffalo, NY", "$options": "i" } },
      "projection": { "position": 1, "location": 1, "_id": 0 }
    }
    
    Example Question: "How many positions are currently present from each city?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {},
      "aggregation": [
        {
          "$group": {
            "_id": "$location",
            "total_positions": { "$sum": 1 }
          }
        }
      ]
    }

    Example Question: "What are the positions that require 2-5 years of experience?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {
        "experience": "2-5 years"
      },
      "projection": {
        "position": 1,
        "experience":1,
        "_id": 0
      }
    }

    Example Question: "What is the contact phone number for Tony Rupp?"
    Expected MongoDB Query:
    {
        "collection": "teams",
        "query": {
            "name": {
                "$regex": "Tony Rupp",
                "$options": "i"
            }
        },
        "projection": {
            "name":1,
            "phone": 1,
            "_id": 0
        }
    }

    Example Question: "What is the pay rate for paralegal roles in Buffalo?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {
        "position": { "$regex": "Paralegal", "$options": "i" },
        "location": "Buffalo, NY"
      },
      "projection": {
        "position": 1,
        "compensation": 1,
        "pay type": 1,
        "location": 1,
        "_id": 0
      }
    }

    Example Question: "What is the compensation range for a Labor & Employment Associate?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {
        "position": { "$regex": "Labor & Employment Associate", "$options": "i" }
      },
      "projection": {
        "position": 1,
        "compensation": 1,
        "location": 1,
        "_id": 0
      }
    }

    Example Question: "How many positions are available in each city?"
    Expected MongoDB Query:
    {
      "collection": "careers",
      "query": {},
      "aggregation": [
        {
          "$group": {
            "_id": "$location",
            "total_positions": { "$sum": 1 }
          }
        },
        {
          "$project": {
            "city": "$_id",
            "_id": 0,
            "total_positions": 1
          }
        }
      ]
    }

    Example Question: "Which articles focus on the Finance area?"
    Expected MongoDB Query:
    {
      "collection": "articles",
      "query": {
        "area": "Finance"
      },
      "projection": {
        "title": 1,
        "area": 1,
        "_id": 0
      }
    }

    Example Question: "List articles discussing succession planning."
    Expected MongoDB Query:
    {
      "collection": "articles",
      "query": {
        "body": {
          "$regex": "succession planning",
          "$options": "i"
        }
      },
      "projection": {
        "title": 1,
        "_id": 0
      },
      "limit": 5
    }

    Example Question: "Are there any articles discussing the Construction industry?"
    Expected MongoDB Query:
    {
      "collection": "articles",
      "query": {
        "body": {
          "$regex": "Construction",
          "$options": "i"
        }
      },
      "projection": {
        "title": 1,
        "_id": 0
      },
       "limit": 5
    }

    Example Question: "What are the specializations under Business Law"
    Expected MongoDB Query:
    {
      "collection": "practices",
      "query": {
        "title": "Business Law"
      },
      "projection": {
        "specializations": 1,
        "title": 1,
        "_id": 0
      }
    }

    Example Question: "Show all team members in the Immigration Law practice."
    Expected MongoDB Query:
    {
      "collection": "practices",
      "query": {
        "title": "Immigration Law"
      },
      "projection": {
        "team members": 1,
        "firm": 1,
        "title": 1,
        "_id": 0
      }
    }

    Example Question: "Who are the leaders in the Environmental Law practice?"
    Expected MongoDB Query:
    {
      "collection": "practices",
      "query": {
        "title": "Environmental Law"
      },
      "projection": {
        "leaders": 1,
        "firm": 1,
        "title": 1,
        "_id": 0
      }
    }

    Example Question: "Which practices involve regulatory compliance?"
    Expected MongoDB Query:
    {
      "collection": "practices",
      "query": {
        "specializations": {
          "$elemMatch": {
            "$regex": "compliance",
            "$options": "i"
          }
        }
      },
      "projection": {
        "title": 1,
        "firm": 1,
        "_id": 0
      }
    }

    Example Question: "List all members who work in Environmental Law."
    Expected MongoDB Query:
    {
      "collection": "practices",
      "query": {
        "title": "Environmental Law"
      },
      "projection": {
        "team members": 1,
        "firm": 1,
        "_id": 0
      }
    }

    Question: """ + json.dumps(user_query) + """
    Output only the MongoDB query as JSON:
    """
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system",
                 "content": "You are an assistant that generates MongoDB queries based on user questions and capable of handling general questions."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",
            max_tokens=200,
            temperature=0,
        )
        generated_query = response.choices[0].message.content.strip()
        return json.loads(generated_query)
    except json.JSONDecodeError as json_err:
        return {"error": f"Error parsing JSON query: {json_err}"}
    except Exception as e:
        return {"error": f"Error generating query: {e}"}


def execute_query(query_data, db):
    try:
        collection = db[query_data["collection"]]
        query = query_data.get("query", {})
        projection = query_data.get("projection")
        aggregation = query_data.get("aggregation")
        if aggregation:
            result = list(collection.aggregate(aggregation))
        elif projection:
            result = list(collection.find(query, projection))
        else:
            result = list(collection.find(query))
        return result
    except Exception as e:
        return {"error": str(e)}


def generate_response(results, question):
    try:
        prompt = f"Based on the following data: {json.dumps(results)}, answer the question: '{question}'"
        response = client.chat.completions.create(
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that answers user questions based on the provided data."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"


# Main Chatbot Page Logic
def chatbot_page(database):
    st.title("Chatbot: Data Visionaries")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for chat in st.session_state.chat_history:
        if chat["role"] == "user":
            with st.chat_message("user"):
                st.markdown(chat["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(chat["content"])

    # Capture user input
    user_input = st.chat_input("Type your question here...")
    if user_input:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Display user's input
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate MongoDB query
        query_data = generate_query(user_input)

        if "error" in query_data:
            # Display error
            with st.chat_message("assistant"):
                st.markdown(f"**Error:** {query_data['error']}")
            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {query_data['error']}"})
        else:
            # Execute query and generate response
            results = execute_query(query_data, database)
            if isinstance(results, dict) and "error" in results:
                with st.chat_message("assistant"):
                    st.markdown(f"**Error:** {results['error']}")
                st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {results['error']}"})
            else:
                response = generate_response(results, user_input)
                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
