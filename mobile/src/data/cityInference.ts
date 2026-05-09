export type Coordinates = {
  latitude: number;
  longitude: number;
};

const SUPPORTED_CITY_COORDINATES: Record<string, Coordinates> = {
  Barranquilla: { latitude: 10.9685, longitude: -74.7813 },
  Bogota: { latitude: 4.711, longitude: -74.0721 },
  Bogotá: { latitude: 4.711, longitude: -74.0721 },
  Cali: { latitude: 3.4516, longitude: -76.532 },
  Cartagena: { latitude: 10.391, longitude: -75.4794 },
  Medellin: { latitude: 6.2442, longitude: -75.5812 },
  Medellín: { latitude: 6.2442, longitude: -75.5812 },
};

function distanceSquared(a: Coordinates, b: Coordinates): number {
  const latDiff = a.latitude - b.latitude;
  const lonDiff = a.longitude - b.longitude;
  return (latDiff * latDiff) + (lonDiff * lonDiff);
}

export function inferNearestCity(location: Coordinates, supportedCities: string[]): string {
  const candidates = supportedCities
    .map((city) => ({ city, coordinates: SUPPORTED_CITY_COORDINATES[city] }))
    .filter((item): item is { city: string; coordinates: Coordinates } => Boolean(item.coordinates));

  if (!candidates.length) {
    return supportedCities[0] || "Bogota";
  }

  return candidates.reduce((best, item) => (
    distanceSquared(location, item.coordinates) < distanceSquared(location, best.coordinates)
      ? item
      : best
  ), candidates[0]).city;
}
