"""CLI test harness — Typer app with server, tool, and agent command groups."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Annotated

import typer

from cli.mcp_client import MCPClient, MCPClientError

app = typer.Typer(name="nhtsa-cli", help="NHTSA MCP Server CLI")
server_app = typer.Typer(help="Server management commands")
tool_app = typer.Typer(help="Direct tool invocation commands")
agent_app = typer.Typer(help="LLM agent commands")
app.add_typer(server_app, name="server")
app.add_typer(tool_app, name="tool")
app.add_typer(agent_app, name="agent")

ServerUrl = Annotated[
    str,
    typer.Option("--server-url", "-u", help="MCP server URL"),
]
DEFAULT_URL = "http://127.0.0.1:8000"


def _pp(data: object) -> None:
    """Pretty-print JSON output."""
    typer.echo(json.dumps(data, indent=2, default=str))


def _client(url: str) -> MCPClient:
    return MCPClient(server_url=url)


# --- Server commands ---


@server_app.command()
def health(url: ServerUrl = DEFAULT_URL) -> None:
    """Check server health."""
    try:
        result = _client(url).health()
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@server_app.command("list-tools")
def list_tools(url: ServerUrl = DEFAULT_URL) -> None:
    """List available MCP tools."""
    try:
        result = _client(url).list_tools()
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@server_app.command()
def start(
    transport: Annotated[str, typer.Option(help="Transport: http or stdio")] = "http",
    port: Annotated[int, typer.Option(help="Port for HTTP transport")] = 8000,
    reload: Annotated[bool, typer.Option(help="Enable auto-reload")] = False,
) -> None:
    """Start the MCP server."""
    if transport == "stdio":
        subprocess.run([sys.executable, "-m", "app.main"], check=True)
    else:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]
        if reload:
            cmd.append("--reload")
        subprocess.run(cmd, check=True)


# --- Tool commands ---


@tool_app.command("decode-vin")
def decode_vin(
    vin: str,
    year: Annotated[int | None, typer.Option("--year", "-y", help="Model year")] = None,
    extended: Annotated[bool, typer.Option("--extended", "-e", help="Extended decode")] = False,
    raw: Annotated[bool, typer.Option("--raw", help="Include raw response")] = False,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Decode a VIN."""
    args: dict[str, object] = {"vin": vin}
    if year is not None:
        args["model_year"] = year
    if extended:
        args["extended"] = True
    try:
        result = _client(url).call_tool("decode_vin_tool", args)
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@tool_app.command("ratings-search")
def ratings_search(
    year: int,
    make: str,
    model: str,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Search safety ratings by year/make/model."""
    try:
        result = _client(url).call_tool(
            "ratings_search_tool",
            {"model_year": year, "make": make, "model": model},
        )
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@tool_app.command()
def recalls(
    year: int,
    make: str,
    model: str,
    campaign: Annotated[str | None, typer.Option("--campaign", "-c")] = None,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Search recalls by year/make/model or campaign number."""
    try:
        if campaign:
            result = _client(url).call_tool(
                "recalls_by_campaign_number_tool",
                {"campaign_number": campaign},
            )
        else:
            result = _client(url).call_tool(
                "recalls_by_vehicle_tool",
                {"model_year": year, "make": make, "model": model},
            )
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@tool_app.command()
def complaints(
    year: int,
    make: str,
    model: str,
    odi: Annotated[str | None, typer.Option("--odi")] = None,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Search complaints by year/make/model or ODI number."""
    try:
        if odi:
            result = _client(url).call_tool(
                "complaints_by_odi_number_tool",
                {"odi_number": odi},
            )
        else:
            result = _client(url).call_tool(
                "complaints_by_vehicle_tool",
                {"model_year": year, "make": make, "model": model},
            )
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@tool_app.command()
def carseat(
    zip_code: Annotated[str | None, typer.Option("--zip")] = None,
    state: Annotated[str | None, typer.Option("--state")] = None,
    lat: Annotated[float | None, typer.Option("--lat")] = None,
    long: Annotated[float | None, typer.Option("--long")] = None,
    miles: Annotated[int, typer.Option("--miles")] = 25,
    lang: Annotated[str | None, typer.Option("--lang")] = None,
    cpsweek: Annotated[bool, typer.Option("--cpsweek")] = False,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Find child car seat inspection stations."""
    try:
        if zip_code:
            args: dict[str, object] = {"zip": zip_code}
            if lang:
                args["lang"] = lang
            if cpsweek:
                args["cpsweek"] = True
            result = _client(url).call_tool("carseat_stations_by_zip_tool", args)
        elif state:
            args = {"state": state}
            if lang:
                args["lang"] = lang
            if cpsweek:
                args["cpsweek"] = True
            result = _client(url).call_tool("carseat_stations_by_state_tool", args)
        elif lat is not None and long is not None:
            args = {"lat": lat, "long": long, "miles": miles}
            if lang:
                args["lang"] = lang
            if cpsweek:
                args["cpsweek"] = True
            result = _client(url).call_tool("carseat_stations_by_geo_tool", args)
        else:
            typer.echo("Error: Provide --zip, --state, or --lat/--long", err=True)
            raise typer.Exit(1) from None
        _pp(result)
    except MCPClientError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


# --- Agent commands ---


@agent_app.command()
def ask(
    question: str,
    provider: Annotated[str | None, typer.Option("--provider", "-p")] = None,
    max_steps: Annotated[int, typer.Option("--max-steps")] = 10,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Ask the LLM agent a question about vehicle safety."""
    from app.config import Settings
    from cli.llm_agent import get_provider, run_agent

    settings = Settings(**({"llm_provider": provider} if provider else {}))
    llm = get_provider(settings)
    client = _client(url)

    try:
        answer, _ = run_agent(question, client, llm, max_iterations=max_steps)
        typer.echo(answer)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None


@agent_app.command()
def demo(url: ServerUrl = DEFAULT_URL) -> None:
    """Run a scripted multi-step demo."""
    from app.config import Settings
    from cli.llm_agent import get_provider, run_agent

    settings = Settings()
    llm = get_provider(settings)
    client = _client(url)

    questions = [
        "What are the safety ratings for a 2020 Toyota Camry?",
        "Find all recalls for a 2022 Ford F-150",
        "Decode VIN 1FA6P8AM0G5227539 and summarize the vehicle",
    ]

    for i, q in enumerate(questions, 1):
        typer.echo(f"\n{'=' * 60}")
        typer.echo(f"Demo {i}/{len(questions)}: {q}")
        typer.echo("=" * 60)
        try:
            answer, _ = run_agent(q, client, llm, max_iterations=10)
            typer.echo(answer)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)


@agent_app.command()
def chat(
    provider: Annotated[str | None, typer.Option("--provider", "-p")] = None,
    max_steps: Annotated[int, typer.Option("--max-steps")] = 10,
    url: ServerUrl = DEFAULT_URL,
) -> None:
    """Start an interactive chat session with the LLM agent."""
    from app.config import Settings
    from cli.llm_agent import get_provider, run_agent

    settings = Settings(**({"llm_provider": provider} if provider else {}))
    llm = get_provider(settings)
    client = _client(url)
    history: list[dict[str, object]] = []

    typer.echo("NHTSA Agent Chat (type 'exit' or 'quit' to end)")
    while True:
        try:
            question = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nGoodbye!")
            break

        question = question.strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            typer.echo("Goodbye!")
            break

        try:
            answer, history = run_agent(
                question, client, llm, max_iterations=max_steps, history=history
            )
            typer.echo(answer)
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    app()
