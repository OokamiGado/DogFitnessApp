import os
from django.conf import settings
from django.db import connection


def get_database_size_bytes():
    """Zwraca rozmiar bazy danych w bajtach.
    Dziala natywnie dla PostgreSQL (np. Neon) przez pg_database_size().
    Dla SQLite (np. lokalny dev bez Postgresa) liczy rozmiar pliku .sqlite3.
    Zwraca None jesli nie da sie ustalic (np. inny silnik bazy)."""
    try:
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_database_size(current_database())")
                row = cursor.fetchone()
                return row[0] if row else None
        elif connection.vendor == 'sqlite':
            db_path = connection.settings_dict.get('NAME')
            if db_path and os.path.exists(str(db_path)):
                return os.path.getsize(str(db_path))
        return None
    except Exception:
        return None


def get_media_size_bytes(media_root=None):
    """Zwraca (rozmiar_w_bajtach, liczba_plikow) dla calego folderu MEDIA_ROOT
    (wszystkie zdjecia cwiczen i inne pliki media)."""
    media_root = media_root or settings.MEDIA_ROOT
    total = 0
    file_count = 0
    if not os.path.exists(media_root):
        return 0, 0
    for dirpath, _dirnames, filenames in os.walk(media_root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if os.path.isfile(fpath):
                try:
                    total += os.path.getsize(fpath)
                    file_count += 1
                except OSError:
                    pass
    return total, file_count


def bytes_to_mb(num_bytes):
    if num_bytes is None:
        return None
    return round(num_bytes / (1024 * 1024), 2)


def get_largest_images(limit=5):
    """Zwraca liste najwiekszych zdjec cwiczen (do wykrywania 'cieżkich' plikow)."""
    from exercises.models import ExerciseImage

    results = []
    for img in ExerciseImage.objects.select_related('exercise').all():
        try:
            size = img.image.size
        except Exception:
            continue
        results.append({
            'exercise_name': img.exercise.name,
            'size_bytes': size,
            'size_mb': bytes_to_mb(size),
            'url': img.image.url,
        })
    results.sort(key=lambda x: x['size_bytes'], reverse=True)
    return results[:limit]


def get_cloudinary_usage():
    """Zwraca podsumowanie uzycia Cloudinary (storage, bandwidth, plan) jesli
    USE_CLOUDINARY=True w settings i pakiet 'cloudinary' jest zainstalowany
    oraz skonfigurowany poprawnymi danymi (CLOUD_NAME/API_KEY/API_SECRET).

    Zwraca None w KAZDYM przypadku gdy dane sa niedostepne - brak konfiguracji,
    brak pakietu, blad sieci/autoryzacji. Dzieki temu wywolanie tej funkcji
    jest zawsze bezpieczne i nigdy nie wywali strony, nawet jesli Cloudinary
    nie jest (jeszcze) poprawnie skonfigurowane."""
    from django.conf import settings

    if not getattr(settings, 'USE_CLOUDINARY', False):
        return None

    try:
        import cloudinary.api
        result = cloudinary.api.usage()

        storage_bytes = result.get('storage', {}).get('usage')
        bandwidth_bytes = result.get('bandwidth', {}).get('usage')

        return {
            'storage_bytes': storage_bytes,
            'storage_mb': bytes_to_mb(storage_bytes),
            'bandwidth_bytes': bandwidth_bytes,
            'bandwidth_mb': bytes_to_mb(bandwidth_bytes),
            'credits_used': result.get('credits', {}).get('usage'),
            'credits_limit': result.get('credits', {}).get('limit'),
            'plan': result.get('plan'),
            'objects_count': result.get('objects', {}).get('usage'),
        }
    except Exception:
        return None
