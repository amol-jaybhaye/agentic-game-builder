import os
import sys
from agent.orchestrator import run_agent

def read_multiline_stdin() -> str:
    data = sys.stdin.read()
    return data.strip()

def main():
    idea = None

    if len(sys.argv) > 1:
        idea = " ".join(sys.argv[1:]).strip()

    if not idea:
        idea = read_multiline_stdin()

    if not idea:
        print("ERROR: No game idea provided.")
        sys.exit(1)

    output_dir = os.environ.get("OUTPUT_DIR", "./output")
    os.makedirs(output_dir, exist_ok=True)

    run_agent(initial_idea=idea, output_dir=output_dir)

if __name__ == "__main__":
    main()
