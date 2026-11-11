"""
plans/templatetags/plan_extras.py

Custom template filters dla modulu 'plans'.

NAPRAWIA BUG: w plan_detail.html (wprowadzony w Etapie 1-2) uzyto
nieprawidlowej skladni Django template language:
    {% with shared=dog.get_shared_tags:pe.exercise %}
Django template language NIE pozwala wywolywac metod z argumentami
w ten sposob (dog.get_shared_tags zwraca <bound method>, a ":pe.exercise"
nie jest poprawnym filtrem) - powodowalo to TemplateSyntaxError i
calkowicie blokowalo renderowanie strony szczegolow planu.

Rozwiazanie: wlasny filtr szablonu, uzywany jako:
    {% load plan_extras %}
    {% with shared=dog|get_shared_tags:pe.exercise %}
"""

from django import template

register = template.Library()


@register.filter
def get_shared_tags(dog, exercise):
    """Filtr szablonu: {{ dog|get_shared_tags:exercise }}
    Zwraca liste tagow przeciwwskazan wspolnych dla psa i cwiczenia
    (woła Dog.get_shared_tags(exercise) z modulu clients.models)."""
    if dog is None or exercise is None:
        return []
    return dog.get_shared_tags(exercise)
