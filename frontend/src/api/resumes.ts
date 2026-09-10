import { apiClient } from './client';
import { Resume, ResumeListResponse } from '../types/resume';

export const resumeApi = {
  uploadResume: async (file: File, name?: string): Promise<Resume> => {
    const formData = new FormData();
    formData.append('file', file);
    if (name && name.trim()) {
      formData.append('name', name.trim());
    }

    const { data } = await apiClient.post<Resume>('/resumes/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  getResumes: async (): Promise<ResumeListResponse> => {
    const { data } = await apiClient.get<ResumeListResponse>('/resumes');
    return data;
  },

  getResume: async (id: string): Promise<Resume> => {
    const { data } = await apiClient.get<Resume>(`/resumes/${id}`);
    return data;
  },

  setPrimaryResume: async (id: string): Promise<Resume> => {
    const { data } = await apiClient.patch<Resume>(`/resumes/${id}/primary`);
    return data;
  },

  updateResumeName: async (id: string, name: string): Promise<Resume> => {
    const { data } = await apiClient.patch<Resume>(`/resumes/${id}`, { name });
    return data;
  },

  deleteResume: async (id: string): Promise<void> => {
    await apiClient.delete(`/resumes/${id}`);
  },

  downloadResume: async (id: string, filename: string): Promise<void> => {
    const response = await apiClient.get(`/resumes/${id}/download`, {
      responseType: 'blob',
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  getResumeSections: async (id: string) => {
    const { data } = await apiClient.get(`/resumes/${id}/sections`);
    return data;
  },

  getResumeText: async (id: string) => {
    const { data } = await apiClient.get(`/resumes/${id}/text`);
    return data;
  },

  parseResume: async (id: string) => {
    const { data } = await apiClient.post(`/resumes/${id}/parse`);
    return data;
  },
};

