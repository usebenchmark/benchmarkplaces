class SourceError(Exception):
    def __init__(self, message, response):
        self.message = message

        try:
            self.text = response.json()
        except ValueError:
            self.text = response.text

    def __str__(self):
        return repr(self.message)
