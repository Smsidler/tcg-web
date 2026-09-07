from django.http import HttpResponse


def home(request):
    return HttpResponse("<h1>Mi tienda Pokémon TCG</h1>")