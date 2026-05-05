import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { costApi } from '../api/cost'

export function useCostSummary() {
  return useQuery({
    queryKey: ['cost'],
    queryFn: costApi.summary,
    refetchInterval: 10000,
  })
}

export function useReconcile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: costApi.reconcile,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cost'] }),
  })
}
