import os
import markdown
from django.shortcuts import render
from django.utils.safestring import mark_safe

def readme_user_wiki(request):
    md_path = os.path.join(os.path.dirname(__file__), "content", "README_USER_WIKI.md")

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    html_content = mark_safe(markdown.markdown(md_content))  # Convert Markdown to safe HTML
    
    return render(request, 'wiki_page.html', {'content': html_content})