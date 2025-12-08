class RateLimitException(Exception):
    """Przekroczony limit zapytań API."""
    pass


class TooManyFormatFilteredException(Exception):
    """Zbyt wiele obrazów zostało odrzuconych z powodu niedozwolonego formatu."""
    pass


class TooManyResolutionFilteredException(Exception):
    """Zbyt wiele obrazów zostało odrzuconych z powodu niedopasowanej rozdzielczości."""
    pass

class TooManyFilesizeFilteredException(Exception):
    """Zbyt wiele obrazów zostało odrzuconych z powodu filtru wagi pliku."""
    pass

class SourceExhaustedException(Exception):
    """Źródło nie zwraca już więcej wyników dla danego zapytania."""
    pass
