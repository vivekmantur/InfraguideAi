import { IGNORED_UPLOAD_PARTS } from "../constants";

export function analyzableFiles(files: File[]) {
  return files.filter((file) => {
    const path = file.webkitRelativePath || file.name;
    const parts = path.split(/[\\/]/);
    return !parts.some((part) => IGNORED_UPLOAD_PARTS.has(part));
  });
}
