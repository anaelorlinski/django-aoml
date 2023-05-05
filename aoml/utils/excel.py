"""ExcelResponse for emencia.django.newsletter"""
# Based on http://www.djangosnippets.org/snippets/1151/
import datetime
from django.utils import timezone
from django.http import HttpResponse
from django.db.models.query import QuerySet


class ExcelResponse(HttpResponse):
    """ExcelResponse feeded by queryset"""

    def __init__(self, data, output_name='excel_data', headers=None,
                 force_csv=False, encoding='utf8'):
        current_tz = timezone.get_current_timezone()

        valid_data = False
        if isinstance(data, QuerySet):
            data = list(data.values())
        if hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                if headers is None:
                    headers = list(data[0].keys())
                data = [[row[col] for col in headers] for row in data]
                data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
        assert valid_data is True, "ExcelResponse requires a sequence of sequences"

        import io
        output = io.StringIO()
        # make a csv
        for row in data:
            out_row = []
            for value in row:
                if not isinstance(value, str):
                    value = str(value)
                value = value.encode(encoding)
                out_row.append(value.replace('"', '""'))
            output.write('"%s"\n' %
                            '","'.join(out_row))
        content_type = 'text/csv'
        file_ext = 'csv'
        output.seek(0)
        super(ExcelResponse, self).__init__(content=output.getvalue(),
                                            content_type=content_type)
        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), file_ext)
