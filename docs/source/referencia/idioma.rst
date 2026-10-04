Idioma de los textos (i18n)
===========================

Los mensajes, etiquetas, cabeceras y títulos se muestran en el idioma activo: español (``"es"``, por defecto) o inglés (``"en"``).
Orden de prioridad: ``with language(...)`` → ``set_language(...)`` → variable de entorno ``WALOPY_LANG`` → español. Todos los símbolos
se importan también desde ``walopy``.

Funciones
---------

.. autofunction:: walopy.set_language

.. autofunction:: walopy.get_language

.. autofunction:: walopy.language
