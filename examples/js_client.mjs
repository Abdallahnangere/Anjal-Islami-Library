class AnjalClient {
  constructor({ baseUrl = "https://islamiclibrary.anjalventures.com", apiKey } = {}) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.apiKey = apiKey;
  }

  async get(path, params = {}) {
    const url = new URL(`${this.baseUrl}${path}`);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }

    const res = await fetch(url, {
      headers: this.apiKey ? { "X-API-Key": this.apiKey } : {},
    });

    if (!res.ok) {
      throw new Error(`Request failed: ${res.status} ${res.statusText}`);
    }

    return res.json();
  }

  quranAyah(surah, ayah) {
    return this.get(`/v1/quran/ayah/${surah}/${ayah}`);
  }

  hadithByNumber(collection, hadithNumber) {
    return this.get(`/v1/hadith/${collection}/${hadithNumber}`);
  }

  hijriFromGregorian(dateIso) {
    return this.get("/v1/hijri/from-gregorian", { date: dateIso });
  }

  prayerTimes(country, city) {
    return this.get("/v1/prayer/times", { country, city });
  }

  meta() {
    return this.get("/v1/meta");
  }
}

const client = new AnjalClient({ apiKey: "YOUR_API_KEY" });

console.log("Quran:", await client.quranAyah(1, 1));
console.log("Hadith:", await client.hadithByNumber("bukhari", 15));
console.log("Hijri:", await client.hijriFromGregorian("2026-04-29"));
console.log("Prayer:", await client.prayerTimes("Nigeria", "Lagos Island"));
console.log("Meta:", await client.meta());
