export interface Resume {
  id: string;
  name: string;
  original_filename: string;
  file_type: 'pdf' | 'docx' | 'txt' | string;
  file_size: number;
  is_primary: boolean;
  version_number: number;
  parser_status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  created_at: string;
  updated_at: string;
}

export interface ResumeListResponse {
  items: Resume[];
  total: number;
}

export interface ResumeSection {
  id: string;
  resume_version_id: string;
  section_type: string;
  content: string;
  section_order: number;
}

export interface ResumeSectionsListResponse {
  resume_id: string;
  version_number: number;
  parser_status: string;
  total_sections: number;
  sections: ResumeSection[];
}

export interface ResumeTextResponse {
  resume_id: string;
  version_number: number;
  parser_status: string;
  extracted_text: string | null;
}

