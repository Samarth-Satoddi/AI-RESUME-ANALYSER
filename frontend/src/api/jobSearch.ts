import { apiClient } from './client';

export interface MissingSkillDetail {
  skill_name: string;
  category?: string;
  priority: 'high' | 'medium' | 'low' | string;
}

export interface RankedJobOpportunity {
  job_id: string;
  listing_id: string;
  title: string;
  company?: string;
  location?: string;
  remote_type?: string;
  employment_type?: string;
  salary_min?: number;
  salary_max?: number;
  currency?: string;
  source: string;
  url?: string;
  posted_at?: string;
  description_snippet: string;
  overall_match_score: number;
  skill_score: number;
  keyword_score: number;
  semantic_score: number;
  experience_score: number;
  education_score: number;
  rank_score: number;
  rank: number;
  matched_skills: string[];
  missing_skills: MissingSkillDetail[];
  partial_matches: string[];
  ai_explanation?: string;
  is_saved: boolean;
  application_status: string;
}

export interface JobSearchQuery {
  role: string;
  location?: string;
  remote?: boolean;
  experience?: string;
  employment_type?: string;
  salary_min?: number;
  salary_max?: number;
  skills?: string[];
  keywords?: string[];
  posted_within_days?: number;
  resume_id?: string;
  limit?: number;
}

export interface SearchStatusResponse {
  search_id: string;
  status: 'queued' | 'searching' | 'analyzing' | 'matching' | 'completed' | 'failed' | string;
  jobs_found: number;
  jobs_analyzed: number;
  jobs_matched: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface SearchResultsResponse {
  search_id: string;
  query: Record<string, any>;
  status: string;
  total_results: number;
  results: RankedJobOpportunity[];
}

export interface SearchListItem {
  id: string;
  query_role: string;
  location?: string;
  remote?: boolean;
  status: string;
  jobs_found: number;
  jobs_matched: number;
  created_at: string;
}

export interface SavedJob {
  id: string;
  job_listing_id: string;
  title: string;
  company?: string;
  location?: string;
  remote_type?: string;
  source: string;
  url?: string;
  status: 'discovered' | 'saved' | 'applied' | 'interview' | 'rejected' | 'offer' | string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SearchDefaults {
  target_role?: string;
  location?: string;
  remote: boolean;
  experience_level?: string;
  skills: string[];
  recommended_resume_id?: string;
  recommended_resume_name?: string;
}

export const jobSearchApi = {
  getDefaults: async (): Promise<SearchDefaults> => {
    const { data } = await apiClient.get<SearchDefaults>('/job-search/defaults');
    return data;
  },

  startSearch: async (query: JobSearchQuery): Promise<SearchStatusResponse> => {
    const { data } = await apiClient.post<SearchStatusResponse>('/job-search/search', query);
    return data;
  },

  getSearchStatus: async (searchId: string): Promise<SearchStatusResponse> => {
    const { data } = await apiClient.get<SearchStatusResponse>(`/job-search/searches/${searchId}`);
    return data;
  },

  getSearchResults: async (
    searchId: string,
    filters?: { min_score?: number; remote_only?: boolean; location?: string; sort_by?: string }
  ): Promise<SearchResultsResponse> => {
    const params: Record<string, any> = {};
    if (filters?.min_score !== undefined && filters.min_score > 0) params.min_score = filters.min_score;
    if (filters?.remote_only) params.remote_only = true;
    if (filters?.location) params.location = filters.location;
    if (filters?.sort_by) params.sort_by = filters.sort_by;

    const { data } = await apiClient.get<SearchResultsResponse>(`/job-search/searches/${searchId}/results`, { params });
    return data;
  },

  listSearches: async (): Promise<SearchListItem[]> => {
    const { data } = await apiClient.get<SearchListItem[]>('/job-search/searches');
    return data;
  },

  saveJob: async (listingId: string): Promise<SavedJob> => {
    const { data } = await apiClient.post<SavedJob>(`/job-search/jobs/${listingId}/save`);
    return data;
  },

  unsaveJob: async (listingId: string): Promise<void> => {
    await apiClient.delete(`/job-search/jobs/${listingId}/save`);
  },

  updateApplicationStatus: async (listingId: string, status: string, notes?: string): Promise<SavedJob> => {
    const { data } = await apiClient.patch<SavedJob>(`/job-search/jobs/${listingId}/status`, { status, notes });
    return data;
  },

  getSavedJobs: async (): Promise<SavedJob[]> => {
    const { data } = await apiClient.get<SavedJob[]>('/job-search/saved');
    return data;
  },

  getTopRecommendations: async (limit = 6): Promise<RankedJobOpportunity[]> => {
    const { data } = await apiClient.get<RankedJobOpportunity[]>('/job-search/top-recommendations', {
      params: { limit },
    });
    return data;
  },
};
