import os
import re
from django.shortcuts import render
import markdown
from django.utils.safestring import mark_safe

def readme_user_wiki(request):
    md_path = os.path.join(os.path.dirname(__file__), "content", "README_USER_WIKI.md")

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Add anchors to the headings (h1, h2, h3, etc.)
    def add_anchors_to_headers(md_text):
        # Regex to match headers and create anchors
        def replace_header(match):
            header_level = match.group(1)  # This is the level of the header, e.g., '#', '##'
            header_text = match.group(2).strip()  # Header text itself
            anchor = header_text.lower().replace(" ", "-").replace("_", "-")  # Normalize to URL-safe anchor
            return f'<h{len(header_level)} id="{anchor}">{header_text}</h{len(header_level)}>'  # Correct header tag

        # Apply regex for headers h1-h6
        return re.sub(r'^(#{1,6})\s*(.*)', replace_header, md_text, flags=re.MULTILINE)

    md_content_with_anchors = add_anchors_to_headers(md_content)

    # Convert the updated Markdown content to HTML
    html_content = mark_safe(markdown.markdown(md_content_with_anchors))  # Convert Markdown to safe HTML

    script = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const header = document.querySelector(".navbar"); // or any other element like .navbar
        const headerHeight = header ? header.offsetHeight : 0; // Get the height of the header

        // Smooth scrolling to anchors with an offset for the header
        const smoothScroll = function(event) {
            if (event.target.tagName === 'A' && event.target.hash) {
                event.preventDefault();  // Prevent the default anchor jump

                const targetId = event.target.hash.substring(1);  // Get the ID from the href (without #)
                const targetElement = document.getElementById(targetId);  // Find the element by ID

                if (targetElement) {
                    // Scroll to the target element minus the height of the header
                    window.scrollTo({
                        top: targetElement.offsetTop - headerHeight,  // Adjust for header height
                        behavior: 'smooth'  // Smooth scroll
                    });
                }
            }
        };

        // Attach the smooth scroll event listener to the document
        document.body.addEventListener('click', smoothScroll);
    });
    </script>
    """

    return render(request, 'wiki_page.html', {'content': html_content + script})
