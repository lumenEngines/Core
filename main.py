import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtWidgets import QApplication

# Initialize logging before importing other modules
from core.logger_config import setup_logging
setup_logging()

from api.anthropic_api import AnthropicAPI
from api.anthropic_api2 import AnthropicAPI as AnthropicAPI2
from gui.text_window import TextWindow
from utils.screenshot_worker import ScreenshotWorker
from utils import web_parser
from googlesearch import search
import core.prompting as prompting
from core.project_linker import project_linker
from utils.file_summarizer import project_summarizer
from utils.smart_context_matcher import smart_context_manager
from core.project_manager import project_manager
#import deep
#import deep2

logger = logging.getLogger(__name__)

app = QApplication(sys.argv)
textWindow = TextWindow()
Anthropic_API = AnthropicAPI()
Anthropic_API2 = AnthropicAPI2()
#Deep_API = deep.DeepAPI()
#Deep2 = deep2.DeepAPI2()

def callCompletionAPI(searchText) -> str:
    """
    Calls the appropriate API (Groq or Anthropic) based on user settings.

    Args:
        searchText (str): The text to be processed by the API.

    Returns:
        str: The processed text returned by the API.
    """
    
    try:
        # Build context from multiple sources
        context_parts = []
        
        # Check for accumulated context and prepend it if available
        if hasattr(textWindow, 'context_buffer') and textWindow.context_buffer:
            with textWindow.context_lock:
                context_parts.append("Accumulated context:\n" + textWindow.context_buffer)
                # Clear the context buffer after using it
                textWindow.context_buffer = ""
        
        # Get context information from textWindow if available
        user_requested_context = getattr(textWindow, 'current_project_context_requested', False)
        chat_history_requested = getattr(textWindow, 'current_chat_history_requested', True)  # Default to True for backward compatibility
        selected_file_path = getattr(textWindow, 'current_selected_file_path', None)
        
        # Add selected file context if available
        if selected_file_path:
            try:
                # Read file content
                with open(selected_file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Get file name for display
                file_name = os.path.basename(selected_file_path)
                
                # Try to get file summary if available
                file_summary = None
                try:
                    from project_linker import project_linker
                    if project_linker and hasattr(project_linker, 'get_file_summary'):
                        file_summary = project_linker.get_file_summary(selected_file_path)
                except Exception as e:
                    logger.debug(f"Could not get file summary: {e}")
                
                # Try to get project structure if available
                project_structure = None
                try:
                    from project_linker import project_linker
                    if project_linker and hasattr(project_linker, 'get_project_summary'):
                        project_structure = project_linker.get_project_summary()
                except Exception as e:
                    print(f"Could not get project structure: {e}")
                
                # Build file context
                file_context_parts = [f"Selected File Context:\nFile: {file_name} ({selected_file_path})"]
                
                if file_summary:
                    file_context_parts.append(f"Summary: {file_summary}")
                
                file_context_parts.append(f"Code:\n```\n{file_content}\n```")
                
                if project_structure:
                    file_context_parts.append(f"Project Structure:\n{project_structure}")
                
                file_context = "\n\n".join(file_context_parts)
                context_parts.append(file_context)
                print(f"Added selected file context: {file_name}")
                
            except Exception as e:
                print(f"Error loading selected file context: {e}")
        
        # Smart project context inclusion
        include_context, context_type, context_content = smart_context_manager.should_include_context(
            searchText, user_requested_context
        )
        
        print(f"Context decision: include={include_context}, type={context_type}, content_length={len(context_content) if context_content else 0}")
        
        if include_context and context_content:
            context_parts.append(context_content)
            print(f"Added {context_type} context to prompt")
        
        # Combine all context
        if context_parts:
            full_text = "\n\n".join(context_parts) + "\n\nCurrent request:\n" + searchText
        else:
            full_text = searchText

        if textWindow.isDeepEnabled():
            print("Sent to Groq (Lamma3): ")
            print(full_text)
            formatted_html = Deep_API.send_message_to_deep(full_text)  # Call the method on the instance
            return formatted_html
        else:
            if textWindow.isRegularModeEnabled():
                print("Sent: ")
                print(full_text)
                return Anthropic_API.send_message_to_anthropic(full_text, chat_history_requested)
            else:
                print("Sent: ")
                print(full_text)
                return Deep2.send_message_to_deep(full_text)
    finally:
        # Clear temporary properties after processing
        if hasattr(textWindow, 'current_selected_file_path'):
            textWindow.current_selected_file_path = None
        if hasattr(textWindow, 'current_project_context_requested'):
            textWindow.current_project_context_requested = False
        if hasattr(textWindow, 'current_chat_history_requested'):
            textWindow.current_chat_history_requested = True  # Reset to default


# Converts a user search text into a response generated by the AI

def textHandler(searchText) -> str:
    """
    Converts user search text into a response generated by the AI.
    If live search is enabled, it also incorporates web search results.

    Args:
        searchText (str): The user's search query.

    Returns:
        str: The AI-generated response.
    """
    # Check if this is a standalone instruction for context/project handling
    if searchText.strip().lower() == "clear context":
        if hasattr(textWindow, 'context_buffer'):
            with textWindow.context_lock:
                textWindow.context_buffer = ""
        return "<p>Context buffer cleared.</p>"
    elif searchText.strip().lower() == "show context":
        if hasattr(textWindow, 'context_buffer') and textWindow.context_buffer:
            with textWindow.context_lock:
                return f"<h3>Current Context Buffer:</h3><pre>{textWindow.context_buffer}</pre>"
        else:
            return "<p>Context buffer is empty.</p>"
    elif searchText.strip().lower() == "help":
        help_html = "<h3>Available Commands</h3><ul>"
        help_html += "<li><strong>clear context</strong> - Clear the context buffer</li>"
        help_html += "<li><strong>show context</strong> - Show the current context buffer</li>"
        help_html += "<li><strong>show project</strong> - Show current project information</li>"
        help_html += "<li><strong>list projects</strong> - List all linked projects</li>"
        help_html += "</ul>"
        help_html += "<p>Double Ctrl+C/Cmd+C after copying text to trigger AI processing.</p>"
        return help_html
    elif searchText.strip().lower() == "show project":
        if project_linker.current_project:
            project_summary = project_linker.get_project_summary()
            return f"<h3>Current Project: {project_linker.current_project}</h3><pre>{project_summary}</pre>"
        else:
            return "<p>No project currently selected. Use the Project Manager to link a project.</p>"
    elif searchText.strip().lower() == "list projects":
        linked_projects = project_linker.get_linked_projects()
        if linked_projects:
            projects_html = "<h3>Linked Projects</h3><ul>"
            for project in linked_projects:
                if project == project_linker.current_project:
                    projects_html += f"<li><strong>{project}</strong> (active)</li>"
                else:
                    projects_html += f"<li>{project}</li>"
            projects_html += "</ul>"
            return projects_html
        else:
            return "<p>No projects linked yet. Use the Project Manager to link a project.</p>"
    
    # Regular processing
    if textWindow.is_not_live():
        result = callCompletionAPI(searchText)
        # Save to project history
        project_manager.add_conversation(searchText, result)
        return result
    else:
        try:
            search_results = search(searchText, num=10, stop=10, pause=1)
            # Print the search results
            html_responses = []
            textWindow.resetSources()
            total_word_count = 0
            word_count = 0

            for i, result in enumerate(search_results, start=1):
                print(f"{i}. {result}")
                textWindow.addURLSource(result)
                html_response = web_parser.extract_main_text(result)

                if html_response is None:
                    continue  # Skip this result if it's None

                if total_word_count + word_count > 10000:
                    break

                html_responses.append(html_response)
                total_word_count += word_count
                word_count = len(html_response.split())

            searchText = "provide information on this subject: " + searchText + " This is the extra context: "
            for i, htmlResponse in enumerate(html_responses):
                if not htmlResponse:
                    continue
                searchText += f"\n\n Context {i}: " + htmlResponse
            result = callCompletionAPI(searchText)
            # Save to project history
            project_manager.add_conversation(searchText, result)
            return result
        except Exception as e:
            print(f"Search error: {e}")
            result = callCompletionAPI("I apologize, but the search functionality is currently unavailable. Let me answer based on my knowledge: " + searchText)
            # Save to project history
            project_manager.add_conversation(searchText, result)
            return result


def updateTextWindow(html):
    """
    Updates the text window with new HTML content.

    Args:
        html (str): The HTML content to be added to the text window.

    Returns:
        None
    """
    textWindow.addPage(html)


def main():
    """
    The main function that sets up and runs the application.

    This function initializes the prompting settings, sets up the clipboard handler,
    creates and starts the screenshot worker thread, and runs the main application loop.

    Returns:
        None

    """
    logger.info("Starting main function...")
    
    logger.info("Setting up window...")
    prompting.output = ""
    prompting.model = "claude-3-5-sonnet-20240620"
    textWindow.addClipboardHandler(textHandler)
    textWindow.show()
    print("Window shown")

    # Create and start the screenshot worker thread
    screenshot_worker = ScreenshotWorker(Anthropic_API)
    screenshot_worker.screenshot_updated.connect(updateTextWindow)
    screenshot_worker.start()
    print("Screenshot worker started")

    print("Entering app.exec_...")
    # Remove plt.show(block=True) which may be causing issues
    try:
        app.exec_()
    except Exception as e:
        print(f"Error in app.exec_: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # Initialize prompting variables if they don't exist
        if not hasattr(prompting, 'groqprompt') or not prompting.groqprompt:
            prompting.groqprompt = prompting.system_prompt2
        
        # Clear any auto-selected project to prevent loading issues
        project_linker.current_project = None
        print("Starting fresh session - no projects auto-loaded")
        
        main()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
