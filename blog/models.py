from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse


class Post(models.Model):
    titulo = models.CharField("Título", max_length=200)
    slug = models.SlugField("Slug", unique=True, blank=True)
    resumen = models.TextField("Resumen")
    contenido = models.TextField("Contenido")
    imagen = models.ImageField(
        "Imagen",
        upload_to="blog/",
        blank=True,
        null=True
    )

    # 🔥 NUEVO → para blog tipo revista
    destacado = models.BooleanField("Destacado", default=False)

    creado = models.DateTimeField("Fecha de creación", auto_now_add=True)
    publicado = models.BooleanField("Publicado", default=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comentarios"
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    texto = models.TextField("Comentario")
    creado = models.DateTimeField("Fecha", auto_now_add=True)
    aprobado = models.BooleanField("Aprobado", default=False)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"

    def __str__(self):
        return f"Comentario de {self.usuario.username} en {self.post.titulo}"