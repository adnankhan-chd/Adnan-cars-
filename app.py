"""Car Price Estimator: upload or paste car photos and get an AI price estimate.

UI: Streamlit | AI: Google Gemini Flash (via the google-genai SDK)
"""

import io
import os
from typing import List, Optional

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-2.5-flash"  # override with GEMINI_MODEL in secrets/env
MAX_IMAGES = 6
MAX_IMAGE_SIDE = 1600  # px; downscale big photos to save tokens and time
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "INR", "AED", "SAR"]


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------
class CarEstimate(BaseModel):
    is_car: bool = Field(description="True if the photos clearly show a car.")
    make: Optional[str] = Field(default=None, description="Manufacturer, e.g. Toyota.")
    model: Optional[str] = Field(default=None, description="Model, e.g. Corolla.")
    year_range: Optional[str] = Field(default=None, description="Likely years, e.g. 2016-2019.")
    body_type: Optional[str] = Field(default=None, description="Sedan, SUV, hatchback, etc.")
    color: Optional[str] = Field(default=None)
    condition: Optional[str] = Field(
        default=None, description="Excellent, Good, Fair or Poor, based on visible state."
    )
    visible_issues: List[str] = Field(
        default_factory=list, description="Visible dents, scratches, rust, worn tires, etc."
    )
    price_low: Optional[float] = Field(default=None, description="Low end of price range.")
    price_high: Optional[float] = Field(default=None, description="High end of price range.")
    price_best_guess: Optional[float] = Field(default=None, description="Most likely price.")
    confidence: Optional[str] = Field(default=None, description="Low, Medium or High.")
    reasoning: Optional[str] = Field(default=None, description="Short explanation of the estimate.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_api_key() -> Optional[str]:
    """Read the Gemini key from Streamlit secrets first, then environment."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets.toml present
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_model_name() -> str:
    try:
        if "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL)


def prepare_image(file) -> Image.Image:
    """Open an uploaded image, fix orientation, convert to RGB and downscale."""
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    return img


def image_to_part(img: Image.Image) -> types.Part:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def build_prompt(currency: str, country: str, mileage: str, extra: str) -> str:
    return f"""You are an experienced used-car appraiser.
Look at the attached car photo(s) and estimate the current USED market price.

Context from the seller:
- Currency for all prices: {currency}
- Country / market: {country or "not specified"}
- Mileage: {mileage or "not specified"}
- Extra notes: {extra or "none"}

Rules:
- If the photos do not clearly show a car, set is_car to false and leave the rest empty.
- Identify make, model and likely year range from the photos only. Do not invent details.
- Judge condition only from what is visible and list any visible issues.
- Give a realistic price range (price_low, price_high) and a best guess, all as plain
  numbers in {currency} with no symbols or commas.
- If mileage is unknown, assume average mileage for the age and say so in reasoning.
- Use "Low" confidence when the photos are few, blurry, or the model is uncertain.
- Keep reasoning under 80 words."""


def estimate_price(images: List[Image.Image], prompt: str) -> CarEstimate:
    client = genai.Client(api_key=get_api_key())
    contents = [image_to_part(i) for i in images] + [prompt]
    response = client.models.generate_content(
        model=get_model_name(),
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CarEstimate,
            temperature=0.2,
        ),
    )
    if getattr(response, "parsed", None) is not None:
        return response.parsed
    # Fallback: parse the raw JSON text ourselves
    return CarEstimate.model_validate_json(response.text)


def money(value: Optional[float], currency: str) -> str:
    return f"{value:,.0f} {currency}" if value is not None else "N/A"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Car Price Estimator", page_icon="🚗", layout="centered")
    st.title("🚗 Car Price Estimator")
    st.caption("Upload or paste photos of your car and get an AI price estimate.")

    if not get_api_key():
        st.error(
            "No Gemini API key found. Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` "
            "(local) or to the app's Secrets settings (Streamlit Cloud)."
        )
        st.stop()

    files = st.file_uploader(
        f"Car photos (up to {MAX_IMAGES}). Click the box and press Ctrl+V / Cmd+V to paste.",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    with st.expander("Optional details (improves accuracy)"):
        col1, col2 = st.columns(2)
        currency = col1.selectbox("Currency", CURRENCIES, index=0)
        country = col2.text_input("Country / market", placeholder="e.g. United States")
        mileage = st.text_input("Mileage", placeholder="e.g. 85,000 km")
        extra = st.text_area("Notes", placeholder="e.g. one owner, new tires, service history")

    images: List[Image.Image] = []
    if files:
        if len(files) > MAX_IMAGES:
            st.warning(f"Only the first {MAX_IMAGES} photos will be used.")
            files = files[:MAX_IMAGES]
        for f in files:
            try:
                images.append(prepare_image(f))
            except Exception:
                st.warning(f"Could not read {f.name}; skipping it.")
        if images:
            st.image(images, width=160)

    if st.button("Estimate price", type="primary", disabled=not images):
        prompt = build_prompt(currency, country.strip(), mileage.strip(), extra.strip())
        with st.spinner("Analyzing your car..."):
            try:
                result = estimate_price(images, prompt)
            except Exception as exc:
                st.error(f"Something went wrong while contacting Gemini: {exc}")
                st.stop()

        if not result.is_car:
            st.warning("These photos don't appear to show a car. Please try different photos.")
            st.stop()

        title = " ".join(x for x in [result.make, result.model] if x) or "Your car"
        st.subheader(title)
        st.metric("Estimated price", money(result.price_best_guess, currency))
        st.write(
            f"**Range:** {money(result.price_low, currency)} to {money(result.price_high, currency)}"
        )

        c1, c2, c3 = st.columns(3)
        c1.write(f"**Year:** {result.year_range or 'N/A'}")
        c2.write(f"**Condition:** {result.condition or 'N/A'}")
        c3.write(f"**Confidence:** {result.confidence or 'N/A'}")
        st.write(f"**Body / color:** {result.body_type or 'N/A'} / {result.color or 'N/A'}")

        if result.visible_issues:
            st.write("**Visible issues:**")
            for issue in result.visible_issues:
                st.write(f"- {issue}")
        if result.reasoning:
            st.info(result.reasoning)

    st.divider()
    st.caption(
        "Estimates come from AI analysis of photos only and are not a professional appraisal. "
        "Check local listings and get an inspection before buying or selling."
    )


if __name__ == "__main__":
    main()
  
