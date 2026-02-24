import { useCallback, useEffect, useRef, useState } from "react";

export default function useDebouncedSearch(onSearch, delay = 300, minChars = 2) {
  const [searchInput, setSearchInput] = useState("");
  const debounceRef = useRef(null);

  const handleSearchInput = useCallback(
    (value) => {
      setSearchInput(value);

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        if (value.length >= minChars || value.length === 0) {
          onSearch(value);
        }
      }, delay);
    },
    [onSearch, delay, minChars]
  );

  const clearSearch = useCallback(() => {
    setSearchInput("");
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    onSearch("");
  }, [onSearch]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return { searchInput, setSearchInput, handleSearchInput, clearSearch };
}
