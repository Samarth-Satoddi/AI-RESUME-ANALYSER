import { apiClient } from './client';

export interface FullAnalysisResponse {
  analysis_id?: string;
  resume_id: string;
  resume_name: string;
  job_id?: string;
  job_title?: string;
  overall_score: number;
  ats_score: number;
  skill_score: number;
  experience_score: number;
  education_score: number;
  keyword_score: number;
  semantic_score: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  skills_detected_count: number;
  matched_skills: string[];
  missing_skills: { name: string; priority: string; category?: string }[];
  roadmap_item_count: number;
  interview_question_count: number;
}

export interface AnalysisListItem {
  id: string;
  resume_id: string;
  resume_name: string;
  job_id?: string;
  job_title?: string;
  overall_score?: number;
  ats_score?: number;
  skill_score?: number;
  status: string;
  created_at: string;
}

export interface SkillMatchItem {
  skill_name: string;
  resume_skill?: string;
  job_skill?: string;
  match_type: string;
  similarity_score: number;
  importance?: string;
}

export interface MissingSkillItem {
  skill_name: string;
  category?: string;
  priority: string;
  reason?: string;
}

export interface RecommendationItem {
  title: string;
  description: string;
  priority: string;
  recommendation_type: string;
}

export interface AnalysisDetail {
  id: string;
  status: string;
  overall_score?: number;
  resume_score?: number;
  ats_score?: number;
  skill_score?: number;
  keyword_score?: number;
  semantic_score?: number;
  experience_score?: number;
  education_score?: number;
  resume_id: string;
  resume_name: string;
  job_id?: string;
  job_title?: string;
  skill_matches: SkillMatchItem[];
  missing_skills: MissingSkillItem[];
  recommendations: RecommendationItem[];
  created_at: string;
  completed_at?: string;
}

export interface RoadmapItem {
  id: string;
  skill_name: string;
  topic: string;
  priority: string;
  estimated_days: number;
  prerequisites?: string[];
  order_index: number;
}

export interface RoadmapResponse {
  id: string;
  title: string;
  description?: string;
  estimated_days?: number;
  items: RoadmapItem[];
}

export interface InterviewQuestion {
  id: string;
  category: string;
  question: string;
  difficulty: string;
  why_it_matters?: string;
  answer_guidance?: string;
}

export interface BulletImprovement {
  original: string;
  improved: string;
  rationale: string;
}

export const analysisApi = {
  runAnalysis: async (payload: { resume_id: string; job_id?: string }): Promise<FullAnalysisResponse> => {
    const { data } = await apiClient.post<FullAnalysisResponse>('/analyses', payload);
    return data;
  },

  getAnalyses: async (): Promise<AnalysisListItem[]> => {
    const { data } = await apiClient.get<AnalysisListItem[]>('/analyses');
    return data;
  },

  getAnalysis: async (id: string): Promise<AnalysisDetail> => {
    const { data } = await apiClient.get<AnalysisDetail>(`/analyses/${id}`);
    return data;
  },

  getRoadmap: async (analysisId: string): Promise<RoadmapResponse> => {
    const { data } = await apiClient.get<RoadmapResponse>(`/analyses/${analysisId}/roadmap`);
    return data;
  },

  getInterviewQuestions: async (analysisId: string): Promise<InterviewQuestion[]> => {
    const { data } = await apiClient.get<InterviewQuestion[]>(`/analyses/${analysisId}/interview`);
    return data;
  },

  improveBullet: async (payload: { bullet: string; target_role?: string }): Promise<BulletImprovement> => {
    const { data } = await apiClient.post<BulletImprovement>('/ai/improve-bullet', payload);
    return data;
  },

  getResumeScore: async (resumeId: string): Promise<FullAnalysisResponse> => {
    const { data } = await apiClient.get<FullAnalysisResponse>(`/resumes/${resumeId}/score`);
    return data;
  },

  getResumeSkills: async (resumeId: string) => {
    const { data } = await apiClient.get(`/resumes/${resumeId}/skills`);
    return data;
  },

  getResumeEntities: async (resumeId: string) => {
    const { data } = await apiClient.get(`/resumes/${resumeId}/entities`);
    return data;
  },
};
