from django.shortcuts import render
from blog.models import Post

def home(request):
    posts = Post.objects.filter(publicado=True)[:3]  # Mostrar los 3 más recientes
    return render(request, "core/home.html", {"posts": posts})

