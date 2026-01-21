from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comentario


def blog_list(request):
    posts = Post.objects.filter(publicado=True)
    return render(request, "blog/blog_list.html", {
        "posts": posts
    })


def blog_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, publicado=True)
    comentarios = post.comentarios.filter(aprobado=True)

    if request.method == "POST" and request.user.is_authenticated:
        texto = request.POST.get("texto")
        if texto:
            Comentario.objects.create(
                post=post,
                usuario=request.user,
                texto=texto
            )
            return redirect("blog:detail", slug=slug)

    return render(request, "blog/blog_detail.html", {
        "post": post,
        "comentarios": comentarios
    })