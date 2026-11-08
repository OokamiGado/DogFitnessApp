from django.core.management.base import BaseCommand
from exercises.models import Exercise, ContraindicationTag


FINAL_TAGS = [
    "Wysokie obciazenie stawow",
    "Odpowiednie przy rehabilitacji stawow",
    "Konczyny miedniczne (KKM)",
    "Konczyny przednie (KKP)",
    "Kregoslup / grzbiet",
    "Skoki / dynamika",
    "Szyja",
    "Klus / bieg",
    "Balans / niestabilne powierzchnie"
]


EXERCISE_TAG_MAPPING = [
    {
        "name": "Tylne lapy - wyciaganie w pozycji wyprostowanej",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Kregoslup / grzbiet",
            "Szyja"
        ]
    },
    {
        "name": "Plecy - cookie-stretching do bokow",
        "variant_name": "",
        "tags": [
            "Kregoslup / grzbiet"
        ]
    },
    {
        "name": "Cavaletti (szczeniak)",
        "variant_name": "Dla szczeniaka",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Sciezka sensoryczna (podstawowa)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Obroty (szczeniak)",
        "variant_name": "",
        "tags": []
    },
    {
        "name": "Target przednimi lapami (szczeniak)",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Bierki (szczeniak)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Wchodzenie 4 lapami na przedmiot (szczeniak)",
        "variant_name": "",
        "tags": []
    },
    {
        "name": "Dwie wyspy (szczeniak)",
        "variant_name": "Dla szczeniaka",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Kregoslup / grzbiet"
        ]
    },
    {
        "name": "Wahadlo na smakolyki (szczeniak)",
        "variant_name": "",
        "tags": []
    },
    {
        "name": "Siad na platformie i wstan do lapki wyzej",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)"
        ]
    },
    {
        "name": "Siad na skosnej platformie - przejscie do deski",
        "variant_name": "",
        "tags": [
            "Kregoslup / grzbiet"
        ]
    },
    {
        "name": "Trzy wyspy (trening obi)",
        "variant_name": "Trening sily (obi)",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Wypady jedna przednia lapa w bok",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Obroty na podwyzszeniu (trening obi)",
        "variant_name": "Trening sily (obi)",
        "tags": []
    },
    {
        "name": "Stabilizacja na dwoch wyspach po przejsciu po luku",
        "variant_name": "Trening sily (obi)",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Hamowanie na targecie przodem + zgiecie w barku (obi)",
        "variant_name": "Trening sily (obi)",
        "tags": [
            "Konczyny przednie (KKP)",
            "Szyja"
        ]
    },
    {
        "name": "Hamowanie na targecie tylem (obi)",
        "variant_name": "Trening sily (obi)",
        "tags": [
            "Klus / bieg",
            "Konczyny miedniczne (KKM)",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Cavaletti (rehabilitacja po KKP)",
        "variant_name": "Rehabilitacja po KKP",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Wchodzenie przednimi lapami na podwyzszenie (rehabilitacja)",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Utrzymywanie pozycji - przod wyzej, tyl na niestabilnej powierzchni",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Kregoslup / grzbiet",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Piwotowanie tylem dookola ustabilizowanego przodu",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Dwie wyspy (rehabilitacja)",
        "variant_name": "Rehabilitacja po KKP",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Trzy wyspy (rehabilitacja)",
        "variant_name": "Rehabilitacja po KKP",
        "tags": [
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Obroty na podwyzszeniu (rehabilitacja)",
        "variant_name": "Rehabilitacja po KKP",
        "tags": [
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Stabilizacja na dwoch wyspach po przejsciu po luku (rehabilitacja)",
        "variant_name": "Rehabilitacja po KKP",
        "tags": [
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Krotkie cavaletti po luku w stepie",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Wypady jedna konczyna piersiowa (rehabilitacja)",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Siad na platformie i wstanie do lapki",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Trzy wyspy",
        "variant_name": "Przygotowawczy",
        "tags": [
            "Kregoslup / grzbiet"
        ]
    },
    {
        "name": "Stabilizacja na dwoch wyspach po zakrecie",
        "variant_name": "Po zakrecie (przygotowawczy)",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Skok na target przez tyczke",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Hamowanie na targecie przodem + zgiecie w barku",
        "variant_name": "Przygotowawczy",
        "tags": [
            "Konczyny przednie (KKP)",
            "Szyja"
        ]
    },
    {
        "name": "Hamowanie na targecie tylem",
        "variant_name": "Przygotowawczy",
        "tags": [
            "Klus / bieg",
            "Konczyny miedniczne (KKM)",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Wolna osemka przez tyczke",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Skok na JumpBox / obrot / zeskok",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Obroty na JB/targecie",
        "variant_name": "",
        "tags": []
    },
    {
        "name": "Szybkie przyspieszenie po obrocie",
        "variant_name": "",
        "tags": [
            "Klus / bieg",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Sciezka sensoryczna po luku",
        "variant_name": "Przygotowawczy (luk)",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Stanie na targecie - wznos do lapki wyzej (senior)",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Kregoslup / grzbiet",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Dynamiczny start ze stania przez tyczke (senior)",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)"
        ]
    },
    {
        "name": "Hamowanie na targecie przodem do zgietego barku (senior)",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Kregoslup / grzbiet",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Schody / sciezka sensoryczna po luku (senior)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny miedniczne (KKM)",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Trzy wyspy (senior)",
        "variant_name": "Senior",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Kregoslup / grzbiet",
            "Odpowiednie przy rehabilitacji stawow"
        ]
    },
    {
        "name": "Gridy",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Obrot i gonienie zabawki",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Skok przez tyczke i powrot",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Wskok na box i zeskok",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Start z siadu przez ogranicznik",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)"
        ]
    },
    {
        "name": "Para 1: Sciezka sensoryczna + cavaletti (koordynacja)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Para 1: Spin na platformie i uwolnienie do miski (sila)",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Para 2: Tyl na niestabilnym, przod na wyzszym stabilnym + target lapa (koordynacja)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Para 2: Krok bokiem z wyzszego targetu (sila)",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Para 3: Przod wysoko, tyl na niestabilnym twardym targecie (koordynacja)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny miedniczne (KKM)"
        ]
    },
    {
        "name": "Para 3: Zeskok z boxa i skok na kolejna platforme (sila)",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)",
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Para 4: Wolna osemka przez tyczke (koordynacja)",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie"
        ]
    },
    {
        "name": "Para 4: Siad na nizszym targecie -> wstanie na wyzszy (sila)",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)"
        ]
    },
    {
        "name": "Skok na boks ze zgieciem barku",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Szyja",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Podskoki przodem",
        "variant_name": "",
        "tags": [
            "Konczyny przednie (KKP)",
            "Skoki / dynamika",
            "Wysokie obciazenie stawow"
        ]
    },
    {
        "name": "Uderzanie w yoga pad i stabilizacja w staniu",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Obrot na boksie - ladowanie przodem - powrot",
        "variant_name": "",
        "tags": [
            "Balans / niestabilne powierzchnie",
            "Konczyny przednie (KKP)"
        ]
    },
    {
        "name": "Piwotowanie tylem z jednej platformy na druga",
        "variant_name": "",
        "tags": [
            "Konczyny miedniczne (KKM)"
        ]
    }
]


class Command(BaseCommand):
    help = (
        "Tworzy startowy slownik tagow przeciwwskazan i automatycznie "
        "przypisuje je do istniejacych cwiczen na podstawie analizy "
        "nazwy/opisu/grup miesniowych. Komenda jest IDEMPOTENTNA - mozna "
        "ja uruchamiac wielokrotnie bez tworzenia duplikatow."
    )

    def handle(self, *args, **options):
        created_tags = 0
        for tag_name in FINAL_TAGS:
            tag, created = ContraindicationTag.objects.get_or_create(name=tag_name)
            if created:
                created_tags += 1
        self.stdout.write(self.style.SUCCESS(
            f"Tagi: {created_tags} nowych, {len(FINAL_TAGS) - created_tags} juz istnialo "
            f"(lacznie {len(FINAL_TAGS)})."
        ))

        tagged_count = 0
        skipped_count = 0
        not_found_count = 0

        for item in EXERCISE_TAG_MAPPING:
            name = item["name"]
            variant_name = item["variant_name"]
            tag_names = item["tags"]

            if not tag_names:
                skipped_count += 1
                continue

            try:
                exercise = Exercise.objects.get(name=name, variant_name=variant_name)
            except Exercise.DoesNotExist:
                not_found_count += 1
                self.stdout.write(self.style.WARNING(
                    f"  Nie znaleziono cwiczenia: '{name}' (wariant: '{variant_name}') - pomijam."
                ))
                continue
            except Exercise.MultipleObjectsReturned:
                exercise = Exercise.objects.filter(name=name, variant_name=variant_name).first()

            tag_objs = ContraindicationTag.objects.filter(name__in=tag_names)
            exercise.contraindication_tags.set(tag_objs)
            tagged_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Otagowano {tagged_count} cwiczen, {skipped_count} bez tagow (OK), "
            f"{not_found_count} nie znaleziono w bazie."
        ))
        self.stdout.write(self.style.SUCCESS("Gotowe! Mozesz skorygowac tagi recznie w /admin/ lub w formularzu cwiczenia."))
