from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from django.contrib.auth import get_user_model
from films.models import Film, UserFilms
from django.views.generic.list import ListView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from films.forms import RegisterForm
from films.utils import get_max_order, reorder

# Create your views here.
class IndexView(TemplateView):
    template_name = 'index.html'
    
class Login(LoginView):
    template_name = 'registration/login.html'

class RegisterView(FormView):
    form_class = RegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        form.save()  # save the user
        return super().form_valid(form)

class FilmList(LoginRequiredMixin, ListView):
    template_name = 'films.html'
    model = Film
    paginate_by = 16
    context_object_name = 'films'

    def get_template_names(self):
        if self.request.htmx:
            return 'partials/film-list-elements.html'
        else:
            return 'films.html'

    def get_queryset(self):
        return UserFilms.objects.filter(user=self.request.user)

def check_username(request):
    username = request.POST.get('username')
    if get_user_model().objects.filter(username=username).exists():
        return HttpResponse("<div id='username-error' class='failure'>This username is already taken</div>")
    else:
        return HttpResponse("<div id='username-error' class='success'>This username is available</div>")

@login_required
def add_film(request):
    title = request.POST.get('film-title')
    (film, new) = Film.objects.get_or_create(title=title)
    if not UserFilms.objects.filter(film=film, user=request.user).exists():
        UserFilms.objects.create(film=film, user=request.user, order=get_max_order(request.user))
    films = UserFilms.objects.filter(user=request.user)
    messages.success(request, f"Added {title} to list")
    return render(request, 'partials/film-list.html', {'films': films})

@login_required
@require_http_methods(['DELETE'])
def delete_film(request, pk):
    UserFilms.objects.get(pk=pk).delete()
    reorder(request.user)
    films = UserFilms.objects.filter(user=request.user)
    return render(request, 'partials/film-list.html', {'films': films})

def search_film(request):
    search_text = request.POST.get('search')
    userfilms = UserFilms.objects.filter(user=request.user)
    results = Film.objects.filter(title__icontains=search_text).exclude(
        title__in=userfilms.values_list('film__title', flat=True)
    )
    context = {'results': results}
    return render(request, 'partials/search-results.html', context)

def clear(request):
    return HttpResponse("")

def sort(request):
    film_pk_order = request.POST.getlist('film_order')
    films = []
    for idx, film_pk in enumerate(film_pk_order, start=1):
        userfilm = UserFilms.objects.get(pk=film_pk)
        userfilm.order = idx
        userfilm.save()
        films.append(userfilm)
    return render(request, 'partials/film-list.html', {'films': films})

@login_required
def detail(request, pk):
    userfilm = get_object_or_404(UserFilms, pk=pk)
    context = {'userfilm': userfilm}
    return render(request, 'partials/film-detail.html', context)

@login_required
def films_partial(request):
    films = UserFilms.objects.filter(user=request.user)
    return render(request, 'partials/film-list.html', {'films': films})

@login_required
def upload_image(request, pk):
    userfilm = get_object_or_404(UserFilms, pk=pk)
    image = request.FILES.get('image')
    userfilm.film.image.save(image.name, image)
    context = {'userfilm': userfilm}
    return render(request, 'partials/film-detail.html', context)
