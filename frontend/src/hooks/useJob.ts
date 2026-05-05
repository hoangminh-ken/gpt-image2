import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { jobsApi } from '../api/jobs'

export function useJob(id: number) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => jobsApi.detail(id),
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'running' || s === 'pending' || s === 'paused' ? 3000 : false
    },
  })
}

export function useJobControls(jobId: number) {
  const qc = useQueryClient()
  const onSuccess = () => {
    qc.invalidateQueries({ queryKey: ['job', jobId] })
    qc.invalidateQueries({ queryKey: ['jobs'] })
  }
  return {
    pause:   useMutation({ mutationFn: () => jobsApi.pause(jobId), onSuccess }),
    resume:  useMutation({ mutationFn: () => jobsApi.resume(jobId), onSuccess }),
    cancel:  useMutation({ mutationFn: () => jobsApi.cancel(jobId), onSuccess }),
    retry:   useMutation({
      mutationFn: (itemId: number) => jobsApi.retryItem(jobId, itemId),
      onSuccess,
    }),
  }
}
