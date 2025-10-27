import json
import inspect
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.api_tools import AVAILABLE_TOOLS

class ReActAgent:
    def __init__(self, agent_id, instructions, available_tools_config, output_schema):
        self.agent_id = agent_id
        self.instructions = instructions
        self.output_schema = output_schema
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro-latest", temperature=0)

        self.tools_config = available_tools_config or []

        # ✅ Safe docstring access — avoids .strip() on None
        self.tool_descriptions = "\n".join(
            [
                f"- {t['name']}: {(AVAILABLE_TOOLS.get(t['name']).__doc__ or 'No documentation provided').strip()}"
                for t in self.tools_config
                if t['name'] in AVAILABLE_TOOLS
            ]
        )

    def run(self, state):
        print(f"--- EXECUTING AGENT: {self.agent_id} ---")

        prompt = f"""
        You are an autonomous agent named '{self.agent_id}'.
        Your instructions are: {self.instructions}

        Current state of the workflow:
        {json.dumps(state, indent=2)}

        You have access to the following tools. You MUST use the exact tool names provided below:
        --- TOOLS ---
        {self.tool_descriptions or 'No tools available.'}
        --- END TOOLS ---

        To use a tool, you must respond with a JSON object containing 'thought' and 'action'.
        The 'thought' is your reasoning for choosing the action.
        The 'action' is a JSON object with 'tool_name' and 'parameters'.

        If you have completed your task and have the final answer, respond with a JSON object containing 'thought' and 'final_answer'.
        The 'final_answer' must conform to this JSON schema:
        {json.dumps(self.output_schema, indent=2)}

        Now, begin. Your response MUST be a single, valid JSON object and nothing else.
        """

        response_json = self._call_llm(prompt)
        output = {}

        if "action" in response_json:
            print(f"Thought: {response_json.get('thought')}")
            action = response_json['action']
            tool_name = action.get('tool_name')
            params = action.get('parameters', {})

           # inside run(), after computing/tool_name and params:
            if tool_name in AVAILABLE_TOOLS:
                print(f"Action: Calling tool '{tool_name}' with parameters: {params}")

                tool_config_for_agent = next((t for t in self.tools_config if t['name'] == tool_name), None)
                if tool_config_for_agent:
                    # Inject every config entry into params (safe)
                    for k, v in (tool_config_for_agent.get('config') or {}).items():
                        # do not overwrite explicit LLM-provided param unless missing
                        if k not in params or params.get(k) in (None, ""):
                            params[k] = v

                    # Optionally confirm required signature params exist. If missing, log clearer message
                    sig = inspect.signature(AVAILABLE_TOOLS[tool_name])
                    missing_required = []
                    for pname, p in sig.parameters.items():
                        if p.default is inspect._empty and pname not in params:
                            missing_required.append(pname)
                    if missing_required:
                        output = {"error": f"Missing required parameters for tool '{tool_name}': {missing_required}"}
                    else:
                        tool_function = AVAILABLE_TOOLS[tool_name]
                        try:
                            observation = tool_function(**params)
                            print(f"Observation: {observation}")
                            output = observation
                        except Exception as e:
                            output = {"error": f"Tool '{tool_name}' raised exception: {e}"}
                else:
                    output = {"error": f"Tool configuration for '{tool_name}' not found for this agent."}
            else:
                output = {"error": f"Tool '{tool_name}' not found."}


        elif "final_answer" in response_json:
            print(f"Thought: {response_json.get('thought')}")
            print("Action: Providing Final Answer.")
            output = response_json['final_answer']

        else:
            print("Error: LLM response did not contain 'action' or 'final_answer'.")
            output = {"error": "Invalid LLM response format."}

        print(f"--- AGENT {self.agent_id} COMPLETED ---")
        return {self.agent_id: {"output": output}}

    def _call_llm(self, prompt):
        """
        Helper function to call the LLM and robustly parse its JSON output.
        It will find the JSON block even if it's surrounded by other text.
        """
        response = self.llm.invoke(prompt)
        content = response.content

        # Handle if content is a list (some LLM responses return list of dicts)
        if isinstance(content, list):
            # Try to extract the main text content
            if len(content) > 0 and isinstance(content[0], dict):
                content = content[0].get("text", "")
            else:
                content = " ".join(str(item) for item in content)

        # Now safely strip
        if isinstance(content, str):
            content = content.strip()
        else:
            content = str(content).strip()


        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
            raise json.JSONDecodeError("No JSON object found", content, 0)
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to decode JSON from LLM for agent {self.agent_id}: {e}")
            print(f"LLM Raw Output:\n{content}")
            return {"error": "Invalid JSON output from LLM."}

    def __call__(self, state):
        return self.run(state.get('steps', {}))
