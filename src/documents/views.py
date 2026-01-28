"""Document views."""

from django.shortcuts import render, get_object_or_404
from documents.models import Document


def document_list(request):
    """List all documents."""
    documents = Document.objects.order_by("-created_at")[:100]
    return render(request, "documents/document_list.html", {"documents": documents})


def document_detail(request, document_id):
    """View document details."""
    document = get_object_or_404(Document, id=document_id)
    return render(request, "documents/document_detail.html", {"document": document})
