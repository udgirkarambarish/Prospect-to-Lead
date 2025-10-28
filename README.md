# Autonomous B2B Prospecting Engine with LangGraph

This project implements an end-to-end autonomous agent system using LangGraph to discover, enrich, score, contact B2B prospects, and learn from feedback. The entire workflow is dynamically configured and orchestrated via a single `workflow.json` file.

## Features

  * **Dynamic Workflow:** Agents and their connections are defined in `workflow.json`, allowing easy modification without code changes.
  * **Multi-Agent System:** Uses specialized agents for distinct tasks (Prospecting, Enrichment, Scoring, Content, Sending, Tracking, Feedback).
  * **ReAct Prompting:** Agents utilize a Reason+Act framework for observable decision-making, powered by Google's Gemini Pro model.
  * **Tool Integration:** Connects to external APIs (Apollo.io, PeopleDataLabs, SendGrid, Google Sheets) via defined tools.
  * **Feedback Loop:** Includes a `FeedbackTrainerAgent` that analyzes campaign results and suggests improvements via Google Sheets (requires human-in-the-loop approval mechanism, not fully implemented in this version).
  * **Rate Limiting:** Incorporates delays between agent steps to manage free-tier API limits.

## Project Structure

/
├── agents/                 \# Contains individual agent implementations
│   ├── **init**.py
│   ├── base\_agent.py         \# ReActAgent base class
│   ├── prospectsearchagent.py
│   ├── dataenrichmentagent.py
│   ├── scoringagent.py
│   ├── outreachcontentagent.py
│   ├── outreachexecutoragent.py \# Or sendoutreachagent.py based on your final naming
│   ├── responsetrackeragent.py
│   └── feedbacktraineragent.py
├── tools/                  \# Contains API tool wrapper functions
│   ├── **init**.py
│   └── api\_tools.py
├── langgraph\_builder.py    \# Main script to build and run the graph
├── workflow.json           \# Defines the agent workflow sequence and configuration
├──.env                    \# Stores API keys and secrets (Gitignored)
└── requirements.txt        \# Python dependencies

````

## Setup Instructions

Follow these steps to set up and run the project:

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and Activate Virtual Environment:**
    It is highly recommended to use Python 3.10.
    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate the environment
    # On Windows:
   .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
    Your terminal prompt should now start with `(venv)`.

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up API Keys (`.env` file):**
    Create a file named `.env` in the root directory of the project. Copy the following content and replace the placeholder values with your actual API keys and IDs. **Never commit this file to Git.**

    ```dotenv
    # Google Gemini API Key (from Google AI Studio)
    GOOGLE_API_KEY="your_gemini_api_key_here"

    # Apollo.io API Key (for search and tracking)
    APOLLO_API_KEY="your_apollo_api_key_here"

    # PeopleDataLabs API Key (for enrichment)
    PEOPLEDATALABS_API_KEY="your_pdl_api_key_here"

    # SendGrid API Key (for sending emails)
    SENDGRID_API_KEY="your_sendgrid_api_key_here"

    # Google Sheet ID (for FeedbackTrainerAgent output)
    SHEET_ID="your_google_sheet_id_here"

    # Path to Google Cloud Service Account JSON key file (for Sheets API)
    GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account.json"
    ```

5.  **Set Up Google Sheets API Credentials:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Select your project.
    *   Enable the **Google Sheets API**.
    *   Go to "APIs & Services" -> "Credentials".
    *   Create a **Service Account**.
    *   Download the JSON key file generated for the service account.
    *   Save this JSON file in your project directory (e.g., as `service-account.json`) and update the `GOOGLE_APPLICATION_CREDENTIALS` path in your `.env` file accordingly.
    *   Open the Google Sheet you specified by `SHEET_ID` in your `.env` file.
    *   Share the sheet with the `client_email` found inside the downloaded service account JSON file, giving it "Editor" permissions.

## Workflow Configuration (`workflow.json`)

The `workflow.json` file is the blueprint for the entire agentic process. It defines:

*   `workflow_name` and `description`.
*   `steps`: An array where each object represents an agent node in the graph.

Each step object includes:
*   `id`: A unique identifier for the agent/step.
*   `agent`: The Python class name of the agent (e.g., `ProspectSearchAgent`).
*   `inputs`: Defines data dependencies from previous steps (e.g., `"{{prospect_search.output.leads}}"`).
*   `instructions`: Natural language goals for the agent.
*   `tools`: A list of tools the agent can use. Each tool is an object with a `name` (matching a function in `api_tools.py`) and a `config` object containing necessary parameters like API keys (using `{{ENV_VAR_NAME}}` placeholders). Agents requiring no external tools have an empty list ``.
*   `output_schema`: Defines the expected structure of the agent's JSON output.

**Example Snippet (`enrichment` step):**
```json
    {
      "id": "enrichment",
      "agent": "DataEnrichmentAgent",
      "inputs": {
        "leads": "{{prospect_search.output.leads}}"
      },
      "instructions": "Enrich lead data using the 'enrich_with_pdl' tool to find company size, technologies used, and the contact's role.",
      "tools":,
      "output_schema": {
        "enriched_leads": [
          {
            "company": "string",
            "contact": "string",
            "role": "string",
            "technologies": "array"
          }
        ]
      }
    }
````

## How to Run

Ensure your virtual environment is active and your `.env` file is correctly configured with your API keys.

Execute the main builder script from the project's root directory:

```bash
python langgraph_builder.py
```

The script will load the `workflow.json`, build the LangGraph, and run the agents sequentially, printing logs including agent thoughts, tool calls, and observations to the console. Delays are included between steps to manage free-tier API rate limits.

## Extension/Modification Guide

The system is designed to be modular and configurable via `workflow.json`.

1.  **Adding a New Agent:**

      * Create a new Python file in the `/agents` directory (e.g., `new_task_agent.py`).
      * Define a class (e.g., `NewTaskAgent`) that inherits from `ReActAgent` (in `base_agent.py`).
      * Implement the agent's specific logic if needed, or rely on the base class ReAct prompting.
      * Add a new step object to the `steps` array in `workflow.json`, specifying the `id`, `agent` class name, `instructions`, `inputs`, `tools`, and `output_schema`.
      * Update the edges in `langgraph_builder.py`'s `main` function if the new agent changes the sequence (though the current builder assumes a linear sequence based on the order in `workflow.json`).

2.  **Adding a New Tool:**

      * Define a new Python function in `tools/api_tools.py` that performs the desired action (e.g., interacts with a new API). Include a clear docstring explaining its purpose and parameters.
      * Add the function to the `AVAILABLE_TOOLS` dictionary at the bottom of `tools/api_tools.py`.
      * In `workflow.json`, add the tool to the `tools` array of any agent step that should have access to it. Make sure the `name` matches the function name and include any necessary `config` (like API key placeholders). The `base_agent.py` prompt will automatically pick up the new tool and its description from the docstring.

3.  **Modifying Workflow Logic:**

      * Change agent `instructions` in `workflow.json` to alter their goals.
      * Adjust the `tools` assigned to each agent.
      * Modify the Ideal Customer Profile (ICP) within the `initial_state` in `langgraph_builder.py`.
      * Reorder steps in `workflow.json` to change the execution sequence (the builder currently creates edges based on array order). For more complex branching or conditional logic, you would need to modify the edge creation logic in `langgraph_builder.py`.

<!-- end list -->

