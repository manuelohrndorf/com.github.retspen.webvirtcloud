import markdown
import os
import re
from django.shortcuts import render
from markdown.extensions.codehilite import CodeHiliteExtension

from django.utils.safestring import mark_safe


def styles():
    return """
    <style>
        pre {
            background-color: #f6f8fa; /* Light gray background */
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #ddd; /* Optional: adds a light border */
            overflow-x: auto;
            white-space: pre-wrap; /* Ensures code wraps properly */
        }

        code {
            font-family: monospace;
            font-size: 14px;
            background-color: #f6f8fa; /* Matches the pre block */
            color: #333;
            padding: 4px 6px;
            border-radius: 4px;
            display: inline-block;
        }
    </style>
    """


def scripts():
    return """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        const header = document.querySelector(".navbar"); // or any other element like .navbar
        const headerHeight = header ? header.offsetHeight : 0; // Get the height of the header

        // Smooth scrolling to anchors with an offset for the header
        const smoothScroll = function(event) {
            if (event.target.tagName === 'A') {
                const href = event.target.getAttribute("href"); // Get the href attribute

                // Check if the href starts with '#' and does not contain any other URL parts
                if (href && href.startsWith("#") && !href.includes("://")) {
                    event.preventDefault(); // Prevent the default anchor jump
                    
                    const targetId = href.substring(1); // Get the ID from href (without #)
                    const targetElement = document.getElementById(targetId); // Find the element by ID

                    if (targetElement) {
                        // Scroll to the target element minus the height of the header
                        window.scrollTo({
                            top: targetElement.offsetTop - headerHeight, // Adjust for header height
                            behavior: 'smooth' // Smooth scroll
                        });
                    }
                }
            }
        };

        // Attach the smooth scroll event listener to the document
        document.body.addEventListener('click', smoothScroll);
    });
    </script>
    """


def add_anchors_to_headers(md_text):
    """Add anchors to Markdown headers while ignoring code blocks."""
    
    # Step 1: Temporarily replace fenced code blocks with placeholders
    fenced_code_blocks = []
    def store_fenced_code(match):
        fenced_code_blocks.append(match.group(0))
        return f"%%CODE_BLOCK_{len(fenced_code_blocks)-1}%%"  # Placeholder

    md_text = re.sub(r'```[\s\S]*?```', store_fenced_code, md_text)

    # Step 2: Temporarily replace inline code (`code`)
    inline_code_blocks = []
    def store_inline_code(match):
        inline_code_blocks.append(match.group(0))
        return f"%%INLINE_CODE_{len(inline_code_blocks)-1}%%"  # Placeholder

    md_text = re.sub(r'`([^`]+)`', store_inline_code, md_text)

    # Step 3: Process only headers (ignoring replaced code blocks)
    def replace_header(match):
        header_level = match.group(1)
        header_text = match.group(2).strip()
        anchor = normalize_anchor(header_text)
        return f'<h{len(header_level)} id="{anchor}">{header_text}</h{len(header_level)}>'

    md_text = re.sub(r'^(#{1,6})\s*(.*)', replace_header, md_text, flags=re.MULTILINE)

    # Step 4: Restore fenced code blocks
    for i, code in enumerate(fenced_code_blocks):
        md_text = md_text.replace(f"%%CODE_BLOCK_{i}%%", code)

    # Step 5: Restore inline code
    for i, code in enumerate(inline_code_blocks):
        md_text = md_text.replace(f"%%INLINE_CODE_{i}%%", code)

    return md_text


def normalize_anchor(header_text):
    # Convert to lowercase
    anchor = header_text.lower()
    # Replace spaces and underscores with hyphens
    anchor = anchor.replace(" ", "-").replace("_", "-")
    # Remove all special characters except hyphens and alphanumeric characters
    anchor = re.sub(r'[^a-z0-9\-]', '', anchor)
    # Ensure there are no consecutive hyphens (replace multiple with a single one)
    anchor = re.sub(r'-+', '-', anchor)
    return anchor


def readme_user_wiki(request):
    md_path = os.path.join(os.path.dirname(__file__), "content", "README_USER_WIKI.md")

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Add anchors to the headings (h1, h2, h3, etc.)
    md_content_with_anchors = add_anchors_to_headers(md_content)

    # Convert the updated Markdown content to HTML
    html_content = mark_safe(markdown.markdown(md_content_with_anchors, extensions=['fenced_code', CodeHiliteExtension()]))

    return render(request, 'wiki_page.html', {'content': html_content + styles() + scripts()})
