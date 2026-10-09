import { useState, useEffect, useCallback } from 'react';

export function useApi(endpoint, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchUrl = endpoint.startsWith('http') ? endpoint : `/api${endpoint}`;

  const fetchData = useCallback(async () => {
    try {
      const response = await fetch(fetchUrl);
      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }
      const result = await response.json();
      setData(result);
      setError(null);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [fetchUrl]);

  useEffect(() => {
    fetchData();

    if (options.pollInterval) {
      const interval = setInterval(fetchData, options.pollInterval);
      return () => clearInterval(interval);
    }
  }, [fetchData, options.pollInterval]);

  return { data, loading, error, refetch: fetchData, lastRefreshed };
}
