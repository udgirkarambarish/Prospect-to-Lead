import json
import os
import importlib
import time
from typing import TypedDict
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    steps: dict

def update_state(current_state: AgentState, new_step_output: dict) -> AgentState:
    current_state['steps'].update(new_step_output)
    return current_state

def load_workflow_config(filepath="workflow.json"):
    with open(filepath, 'r') as f:
        return json.load(f)

def get_config_value(config_dict: dict, key: str):
    placeholder = config_dict.get(key, "")
    if placeholder.startswith("{{") and placeholder.endswith("}}"):
        env_var_name = placeholder[2:-2]
        value = os.getenv(env_var_name)
        if not value:
            raise ValueError(f"Environment variable '{env_var_name}' not set.")
        return value
    return placeholder

def create_agent_instance(step_config):
    agent_class_name = step_config['agent']
    module_name = f"agents.{agent_class_name.lower()}"
    module = importlib.import_module(module_name)
    agent_class = getattr(module, agent_class_name)

    tools_config = step_config.get('tools', [])
    parsed_tools = []

    for tool in tools_config:
        # normalize string tool names to dict form
        if isinstance(tool, str):
            tool_obj = {"name": tool, "config": {}}
        elif isinstance(tool, dict):
            tool_obj = {"name": tool.get("name"), "config": tool.get("config", {})}
        else:
            raise TypeError(f"Unexpected tool format: {tool}")

        # resolve any placeholders in the tool_obj['config']
        cfg = {}
        for k, v in (tool_obj.get('config') or {}).items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                # reuse existing helper; expects placeholder like {{ENV_VAR}}
                env_key = v[2:-2]
                env_val = os.getenv(env_key)
                if env_val is None:
                    raise ValueError(f"Environment variable '{env_key}' not set for tool '{tool_obj['name']}'")
                cfg[k] = env_val
            else:
                cfg[k] = v
        tool_obj['config'] = cfg

        parsed_tools.append(tool_obj)

    agent_instance = agent_class(
        agent_id=step_config['id'],
        instructions=step_config.get('instructions', ''),
        available_tools_config=parsed_tools,
        output_schema=step_config.get('output_schema', {})
    )
    return agent_instance

def main():
    config = load_workflow_config()
    print(f"Starting workflow: {config['workflow_name']}")

    workflow = StateGraph(AgentState)

    for i, step in enumerate(config['steps']):
        print(f"Adding node: {step['id']}")
        
        agent_instance = create_agent_instance(step)
        
        if i == 0:
            node_to_add = agent_instance
        else:
            def create_delayed_wrapper(agent):
                def agent_with_delay(state):
                    delay_seconds = 30
                    print(f"\n--- WAITING {delay_seconds} SECONDS TO AVOID RATE LIMITING ---")
                    time.sleep(delay_seconds) 
                    return agent(state)
                return agent_with_delay
            
            node_to_add = create_delayed_wrapper(agent_instance)

        workflow.add_node(step['id'], lambda state, agent=node_to_add: update_state(state, agent(state)))

    for i, step in enumerate(config['steps']):
        current_step_id = step['id']
        if i == 0:
            workflow.set_entry_point(current_step_id)
        
        if i < len(config['steps']) - 1:
            next_step_id = config['steps'][i+1]['id']
            workflow.add_edge(current_step_id, next_step_id)
        else:
            workflow.add_edge(current_step_id, END)

    app = workflow.compile()

    # Define the initial state with the Ideal Customer Profile (ICP)
    initial_state = {
        "steps": {
            "initial_icp": {
                "industry": "Software",
                "location": "USA",
                "employee_range": "51-200",
                "signals": ["hiring for sales roles"]
            }
        }
    }
    
    print("\n--- RUNNING WORKFLOW ---")
    final_state = app.invoke(initial_state)

    print("\n--- WORKFLOW COMPLETED ---")
    print("Final State:")
    print(json.dumps(final_state, indent=2))

if __name__ == "__main__":
    main()