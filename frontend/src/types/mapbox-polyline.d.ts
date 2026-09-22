declare module '@mapbox/polyline' {
  interface Polyline {
    decode(str: string, precision?: number): Array<[number, number]>
    encode(coordinates: Array<[number, number]>, precision?: number): string
  }

  const polyline: Polyline
  export default polyline
}
