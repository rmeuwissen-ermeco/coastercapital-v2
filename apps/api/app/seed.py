"""Insert a small, idempotent demo catalogue for first deployments."""

from datetime import date

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Coaster, CoasterStatus, Country, Manufacturer, Park


def seed() -> None:
    with SessionLocal.begin() as db:
        country = db.scalar(select(Country).where(Country.code == "NL"))
        if country is None:
            country = Country(code="NL", name="Netherlands")
            db.add(country)
            db.flush()

        park = db.scalar(select(Park).where(Park.slug == "efteling"))
        if park is None:
            park = Park(
                name="Efteling",
                slug="efteling",
                country_id=country.id,
                city="Kaatsheuvel",
                opened_on=date(1952, 5, 31),
                website_url="https://www.efteling.com/",
                summary="Theme park in Kaatsheuvel, Netherlands.",
            )
            db.add(park)
            db.flush()

        manufacturer = db.scalar(
            select(Manufacturer).where(Manufacturer.slug == "bolliger-mabillard")
        )
        if manufacturer is None:
            manufacturer = Manufacturer(
                name="Bolliger & Mabillard",
                slug="bolliger-mabillard",
                country_id=None,
                founded_year=1988,
                website_url="https://www.bolliger-mabillard.com/",
            )
            db.add(manufacturer)
            db.flush()

        coaster = db.scalar(
            select(Coaster).where(
                Coaster.park_id == park.id,
                Coaster.slug == "baron-1898",
            )
        )
        if coaster is None:
            db.add(
                Coaster(
                    name="Baron 1898",
                    slug="baron-1898",
                    park_id=park.id,
                    manufacturer_id=manufacturer.id,
                    status=CoasterStatus.OPERATING,
                    opened_on=date(2015, 7, 1),
                    height_m=37.5,
                    speed_kmh=90,
                    length_m=501,
                    inversions=2,
                    summary="A dive coaster themed around a nineteenth-century mine.",
                )
            )


if __name__ == "__main__":
    seed()
