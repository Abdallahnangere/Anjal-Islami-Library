import requests


class AnjalClient:
    def __init__(self, base_url="https://islamiclibrary.anjalventures.com", api_key=None, timeout=20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def _get(self, path, params=None):
        response = self.session.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def quran_ayah(self, surah, ayah):
        return self._get(f"/v1/quran/ayah/{surah}/{ayah}")

    def hadith_by_number(self, collection, hadith_number):
        return self._get(f"/v1/hadith/{collection}/{hadith_number}")

    def hijri_from_gregorian(self, date_iso):
        return self._get("/v1/hijri/from-gregorian", {"date": date_iso})

    def prayer_times(self, country, city):
        return self._get("/v1/prayer/times", {"country": country, "city": city})

    def meta(self):
        return self._get("/v1/meta")


if __name__ == "__main__":
    client = AnjalClient(api_key="YOUR_API_KEY")

    print("Quran:")
    print(client.quran_ayah(1, 1))

    print("\nHadith:")
    print(client.hadith_by_number("bukhari", 15))

    print("\nHijri:")
    print(client.hijri_from_gregorian("2026-04-29"))

    print("\nPrayer:")
    print(client.prayer_times("Nigeria", "Lagos Island"))

    print("\nMeta:")
    print(client.meta())
