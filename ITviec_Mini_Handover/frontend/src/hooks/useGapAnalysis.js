import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

export const useGapAnalysis = () => {
  const [taskId, setTaskId] = useState(null);

  // 1. API MỚI: Trích xuất CV
  const extractCvMutation = useMutation({
    mutationFn: async (cvText) => {
      const response = await axios.post(`${API_BASE}/extract-cv`, {
        cv_text: cvText,
      });
      return response.data.data; // Trả về cục JSON chứa skill và level
    }
  });
// 1.5 API MỚI: Trích xuất JD ngầm
  const extractJdMutation = useMutation({
    mutationFn: async (jdText) => {
      const response = await axios.post(`${API_BASE}/extract-jd`, { jd_text: jdText });
      return response.data.data;
    }
  });
  // 2. API CŨ: Bắt đầu phân tích Gap (giữ nguyên)
  const analyzeMutation = useMutation({
    mutationFn: async ({ jdText, cvText, verifiedSkills, preExtractedJd }) => { // THÊM param này
      const response = await axios.post(`${API_BASE}/analyze-gap`, {
        jd_text: jdText,
        cv_text: cvText,
        verified_skills: verifiedSkills,
        pre_extracted_jd: preExtractedJd // THÊM param này
      });
      return response.data.task_id;
    },
    onSuccess: (id) => setTaskId(id),
  });

  // 3. API CŨ: Polling (giữ nguyên)
  const pollingQuery = useQuery({
    queryKey: ['taskStatus', taskId],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE}/task-status/${taskId}`);
      return response.data;
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state?.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 3000;
    },
  });

  return {
    extractCv: extractCvMutation.mutateAsync,
    isExtracting: extractCvMutation.isPending,
    extractedSkills: extractCvMutation.data,

    extractJd: extractJdMutation.mutateAsync, // XUẤT RA NÀY
    isExtractingJd: extractJdMutation.isPending, // XUẤT RA NÀY


    startAnalysis: analyzeMutation.mutate,
    isSubmitting: analyzeMutation.isPending,
    pollingStatus: pollingQuery.data?.status, 
    resultData: pollingQuery.data?.data, 
  };
};