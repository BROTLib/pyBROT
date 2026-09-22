from pathlib import Path

from pybrotlib.weather import FileWeatherSource


async def test_json_source_reads_fields(tmp_path: Path) -> None:
    path = tmp_path / "weather.json"
    path.write_text(
        '{"temperature": 12.5, "humidity": 55.0, "pressure": 1013.2, "time": "2026-09-22T10:00:00+00:00"}'
    )

    reading = await FileWeatherSource(path).read()

    assert reading is not None
    assert reading.temperature == 12.5
    assert reading.humidity == 55.0
    assert reading.pressure == 1013.2
    assert reading.time is not None


async def test_yaml_source_reads_fields(tmp_path: Path) -> None:
    path = tmp_path / "weather.yaml"
    path.write_text("temperature: 12.5\nhumidity: 55.0\npressure: 1013.2\n")

    reading = await FileWeatherSource(path).read()

    assert reading is not None
    assert reading.temperature == 12.5
    assert reading.humidity == 55.0
    assert reading.pressure == 1013.2
    assert reading.time is None


async def test_yml_suffix_is_also_treated_as_yaml(tmp_path: Path) -> None:
    path = tmp_path / "weather.yml"
    path.write_text("temperature: 3.0\n")

    reading = await FileWeatherSource(path).read()

    assert reading is not None
    assert reading.temperature == 3.0


async def test_missing_fields_are_none(tmp_path: Path) -> None:
    path = tmp_path / "weather.json"
    path.write_text('{"temperature": 12.5}')

    reading = await FileWeatherSource(path).read()

    assert reading is not None
    assert reading.temperature == 12.5
    assert reading.humidity is None
    assert reading.pressure is None


async def test_missing_file_returns_none(tmp_path: Path) -> None:
    reading = await FileWeatherSource(tmp_path / "does-not-exist.json").read()
    assert reading is None


async def test_malformed_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "weather.json"
    path.write_text("{not valid json")

    reading = await FileWeatherSource(path).read()
    assert reading is None


async def test_malformed_yaml_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "weather.yaml"
    path.write_text("temperature: [1, 2\n")

    reading = await FileWeatherSource(path).read()
    assert reading is None
