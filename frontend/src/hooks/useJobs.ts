import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { jobsApi, type CreateTemplateJob, type Job } from '../api/jobs'

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: jobsApi.list,
    refetchInterval: 5000,
  })
}

export function useCreateJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTemplateJob) => jobsApi.create(body),
    onSuccess: (job: Job) => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['job', job.id] })
    },
  })
}
