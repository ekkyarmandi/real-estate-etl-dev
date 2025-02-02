from scrapy.commands import ScrapyCommand
from scrapy.utils.project import get_project_settings
from reid.extractor.ubudproperty import UbudPropertyExtractor


class ExtractCommand(ScrapyCommand):
    requires_project = True

    def syntax(self):
        return "[options] <extractor>"

    def short_desc(self):
        return "Run a extractor command"

    def run(self, args, opts):
        if len(args) < 1:
            print("Please specify an extractor to run.")
            return

        extractor_name = args[0]
        if extractor_name == "ubudproperty":
            extractor = UbudPropertyExtractor()
            records = extractor.extract()
            print(records)
        else:
            print(f"Extractor '{extractor_name}' not recognized.")
