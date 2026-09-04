import { useQuery } from '@tanstack/react-query';
import { getPatients } from '../api/patients';

export function usePatients(wardId) {
  return useQuery({
    queryKey: ['patients', wardId || 'all'],
    queryFn: () => getPatients({ wardId }),
    staleTime: 15_000,
  });
}
