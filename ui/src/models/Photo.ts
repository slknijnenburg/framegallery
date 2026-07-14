/** ActivePhoto is a source-agnostic reference to the currently displayed photo. */
export default interface ActivePhoto {
  library_id: string;
  external_id: string;
  composite_id: string;
  source_type: string;
  is_local: boolean;
  /** Relative URL to fetch the (display-ready) image bytes. */
  bytes_url: string;
  filename?: string | null;
  width?: number | null;
  height?: number | null;
  aspect_width?: number | null;
  aspect_height?: number | null;
  keywords?: string[] | null;
}
