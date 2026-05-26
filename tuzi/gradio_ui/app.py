"""Gradio web UI for the Tuzi AI Tutor."""

import gradio as gr

from ..database import Database
from ..llm import LLMClient
from ..models import (
    CommunicationStyle,
    Depth,
    LearningStyle,
    ReasoningFramework,
    ToneStyle,
)
from ..session import SessionManager
from .callbacks import ChatCallbacks, SettingsCallbacks


def run_gradio(session_mgr: SessionManager, db: Database, llm: LLMClient):
    """Build and launch the Gradio web interface."""
    chat_cb = ChatCallbacks(session_mgr, llm)
    settings_cb = SettingsCallbacks(session_mgr, db)

    initial_profile = settings_cb.load_profile()

    with gr.Blocks(title="Tuzi AI Tutor") as demo:
        gr.Markdown(
            "# Tuzi AI Tutor\n"
            "Your personal AI tutor powered by Mr. Ranedeer. "
            "Use the **Chat** tab to interact, or configure your profile in **Settings**."
        )

        ui_state = gr.State({
            "session_state": session_mgr.state.value,
            "topic": None,
            "curriculum_id": None,
        })

        with gr.Tabs():
            # ---- Chat Tab ----
            with gr.Tab("Chat"):
                chatbot = gr.Chatbot(label="Conversation", height=500)
                msg = gr.Textbox(
                    label="Your message",
                    placeholder="Type /help for commands, /plan <topic>, or ask a question...",
                )
                with gr.Row():
                    submit_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear Chat")
                status_display = gr.Markdown(
                    f"**State:** {session_mgr.state.value}"
                )

            # ---- Curriculum Tab ----
            with gr.Tab("Curriculum"):
                curriculum_html = gr.HTML(
                    value=(
                        "<p style='color: gray;'>"
                        "No curriculum loaded. Use the Chat tab to /plan a topic."
                        "</p>"
                    )
                )

            # ---- Settings Tab ----
            with gr.Tab("Settings"):
                name_input = gr.Textbox(label="Name", value=initial_profile[0])
                depth_dropdown = gr.Dropdown(
                    label="Depth",
                    choices=[d.value for d in Depth],
                    value=initial_profile[1],
                )
                style_dropdown = gr.Dropdown(
                    label="Learning Style",
                    choices=[s.value for s in LearningStyle],
                    value=initial_profile[2],
                )
                comm_dropdown = gr.Dropdown(
                    label="Communication Style",
                    choices=[c.value for c in CommunicationStyle],
                    value=initial_profile[3],
                )
                tone_dropdown = gr.Dropdown(
                    label="Tone",
                    choices=[t.value for t in ToneStyle],
                    value=initial_profile[4],
                )
                reasoning_dropdown = gr.Dropdown(
                    label="Reasoning Framework",
                    choices=[r.value for r in ReasoningFramework],
                    value=initial_profile[5],
                )
                emojis_checkbox = gr.Checkbox(
                    label="Enable Emojis", value=initial_profile[6]
                )
                language_input = gr.Textbox(
                    label="Language", value=initial_profile[7]
                )
                save_btn = gr.Button("Save Profile", variant="primary")
                config_status = gr.Markdown("")

            # ---- Status Tab ----
            with gr.Tab("Status"):
                status_html = gr.HTML(
                    value=_build_status_html(session_mgr)
                )
                refresh_status_btn = gr.Button("Refresh")

        # ---- Wire Chat callbacks ----
        chat_inputs = [msg, chatbot, ui_state]
        chat_outputs = [chatbot, curriculum_html, status_display, ui_state]

        msg.submit(chat_cb.handle_message, chat_inputs, chat_outputs)
        submit_btn.click(chat_cb.handle_message, chat_inputs, chat_outputs)

        clear_btn.click(
            lambda state: ([], state),
            [ui_state],
            [chatbot, ui_state],
        )

        # ---- Wire Settings callback ----
        save_btn.click(
            settings_cb.save_profile,
            [
                name_input, depth_dropdown, style_dropdown,
                comm_dropdown, tone_dropdown, reasoning_dropdown,
                emojis_checkbox, language_input,
            ],
            [config_status, status_display],
        )

        # ---- Wire Status refresh ----
        refresh_status_btn.click(
            lambda: _build_status_html(session_mgr),
            None,
            [status_html],
        )

    demo.queue(default_concurrency_limit=1)
    demo.launch(server_name="127.0.0.1", server_port=7860, theme=gr.themes.Soft())


def _build_status_html(session_mgr: SessionManager) -> str:
    """Build the status tab HTML content."""
    profile = session_mgr.profile
    state = session_mgr.state.value
    curriculum = session_mgr.curriculum

    lines = ["<div style='font-family: sans-serif; max-width: 600px;'>"]

    if profile:
        lines.append("<h3>Profile</h3><ul>")
        lines.append(f"<li><strong>Depth:</strong> {profile.depth.value}</li>")
        lines.append(f"<li><strong>Learning Style:</strong> {profile.learning_style.value}</li>")
        lines.append(f"<li><strong>Communication:</strong> {profile.communication_style.value}</li>")
        lines.append(f"<li><strong>Tone:</strong> {profile.tone_style.value}</li>")
        lines.append(f"<li><strong>Reasoning:</strong> {profile.reasoning_framework.value}</li>")
        lines.append(f"<li><strong>Emojis:</strong> {'Enabled' if profile.emojis_enabled else 'Disabled'}</li>")
        lines.append(f"<li><strong>Language:</strong> {profile.language}</li>")
        lines.append("</ul>")
    else:
        lines.append("<p style='color: gray;'>No profile configured. Use the Settings tab.</p>")

    lines.append(f"<p><strong>State:</strong> {state}</p>")

    if curriculum:
        total = len(curriculum.prerequisites) + len(curriculum.main_curriculum)
        completed = sum(
            1
            for l in curriculum.prerequisites + curriculum.main_curriculum
            if l.status == "completed"
        )
        lines.append(f"<p><strong>Topic:</strong> {curriculum.topic}</p>")
        lines.append(f"<p><strong>Progress:</strong> {completed}/{total} lessons completed</p>")

        current = session_mgr.session.current_lesson_id
        if current:
            lines.append(f"<p><strong>Current Lesson:</strong> {current}</p>")

    lines.append("</div>")
    return "\n".join(lines)
