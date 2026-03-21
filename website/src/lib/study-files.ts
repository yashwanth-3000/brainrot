export const STUDY_FILE_ACCEPT = ".pdf,.txt,.doc,.docx";
export const STUDY_FILE_HELPER_TEXT = "Attach a PDF, TXT, DOC, or DOCX file (max 20 MB).";
export function isSupportedStudyFile(file: File): boolean {
  const ext = file.name.split(".").pop()?.toLowerCase();
  return ["pdf", "txt", "doc", "docx"].includes(ext ?? "");
}
