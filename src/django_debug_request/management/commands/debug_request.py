import logging
import sys
from django.core.management.base import BaseCommand
from django.db import connections
from django.test.client import Client
from urllib.parse import urlparse


class Command(BaseCommand):
    help = (
        "Call me like I'm cURL! A very stupid cURL, but one that can print SQL queries."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--print-sql",
            action="store_true",
            help="Print all SQL queries.",
        )
        parser.add_argument(
            "url",
            help="Target URL",
        )
        parser.add_argument(
            "-X",
            "--method",
            default="GET",
            help="Method",
        )
        parser.add_argument(
            "-H",
            "--header",
            action="append",
            help="Headers",
        )
        parser.add_argument(
            "--compressed",
            help="For Chrome compatibility, will be ignored",
        )
        parser.add_argument(
            "--data-raw",
            help="Raw data",
        )

    def handle(self, *args, **options):
        h = logging.StreamHandler()
        h.setLevel(logging.DEBUG)
        h.setFormatter(
            logging.Formatter(
                "%(levelname)s %(asctime)s %(name)s %(module)s %(message)s"
            )
        )
        logging.root.setLevel(logging.DEBUG)
        logger = logging.getLogger("debug_request")
        logger.addHandler(h)

        if options["print_sql"]:
            for c in connections.all():
                c.force_debug_cursor = True
            logging.root.manager.loggerDict["django.db.backends"].level = logging.DEBUG
            logging.root.manager.loggerDict["django.db.backends"].addHandler(h)

        u = urlparse(options["url"])
        path = u.path
        if u.query:
            path += "?" + u.query
        c = Client()

        extra = {
            "HTTP_HOST": u.netloc,
        }
        content_type = "application/x-www-form-urlencoded"
        for header in options.get("header") or []:
            k, v = header.split(":", 1)
            extra["HTTP_" + k.upper().strip().replace("-", "_")] = v.lstrip(" ")
            if k.lower().strip() == "content-type":
                content_type = v.lstrip(" ")

        logger.debug(f"Extra array: {extra}")

        r = c.generic(
            method=options["method"],
            path=path,
            data=options["data_raw"],
            secure=u.scheme == "https",
            content_type=content_type,
            **extra,
        )
        logger.debug(f"Response code: {r.status_code}")
        logger.debug(f"Resolver match: {r.resolver_match}")
        for k, v in r.headers.items():
            logger.debug(f"Response header: {k}: {v}")
        sys.stdout.buffer.write(r.content)
