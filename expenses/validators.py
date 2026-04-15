from django.core.exceptions import ValidationError

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def validate_attachment(file):
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(f"Файл больше 10 МБ ({file.size} байт)")
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_MIME:
        raise ValidationError(f"Недопустимый тип файла: {content_type}")
