"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/badge"; // Assuming you have Shadcn UI Badge component
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

// Helper to format date to YYYY-MM
const formatDateToMonthYear = (date) => {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${year}-${month}-01`;
};

// Get current and previous month dates
const getCurrentAndPreviousMonth = () => {
  const currentDate = new Date();
  const previousMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
  return {
    current: formatDateToMonthYear(currentDate),
    previous: formatDateToMonthYear(previousMonth),
  };
};

async function getTagsSummary(date) {
  try {
    const res = await fetch(`http://localhost:8000/tags/?date=${date}`, { cache: "no-store" });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to fetch tags summary" }));
      throw new Error(errorData.detail || "Failed to fetch tags summary");
    }
    return res.json();
  } catch (error) {
    console.error("Error fetching tags summary:", error);
    throw error; // Re-throw to be caught by component
  }
}

async function getTagDetails(tagName, date, page = 1, size = 10) {
  // Default size 10
  try {
    const res = await fetch(`http://localhost:8000/tags/${encodeURIComponent(tagName)}?date=${date}&page=${page}&size=${size}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to fetch tag details" }));
      throw new Error(errorData.detail || "Failed to fetch tag details");
    }
    return res.json();
  } catch (error) {
    console.error("Error fetching tag details:", error);
    throw error;
  }
}

async function updateTagStatus(tagId, statusUpdate) {
  try {
    const res = await fetch(`http://localhost:8000/tags/${tagId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(statusUpdate),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Failed to update tag status" }));
      throw new Error(errorData.detail || "Failed to update tag status");
    }
    return res.json();
  } catch (error) {
    console.error("Error updating tag status:", error);
    throw error;
  }
}

export default function TagsPage() {
  const { current, previous } = getCurrentAndPreviousMonth();
  const [date, setDate] = useState(current);
  const [tagsSummary, setTagsSummary] = useState({});
  const [selectedTag, setSelectedTag] = useState(null);
  const [tagDetails, setTagDetails] = useState({ items: [], total: 0, page: 1, size: 10, pages: 0 });
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [detailsError, setDetailsError] = useState(null);

  // Fetch Summary
  useEffect(() => {
    async function loadTagsSummary() {
      setIsLoadingSummary(true);
      setSummaryError(null);
      setTagsSummary({}); // Clear previous summary
      setSelectedTag(null); // Clear selected tag when date changes
      setTagDetails({ items: [], total: 0, page: 1, size: 10, pages: 0 }); // Clear details
      try {
        const fetchedTags = await getTagsSummary(date);
        setTagsSummary(fetchedTags);
      } catch (err) {
        setSummaryError(err.message);
        toast.error(`Error loading tags summary: ${err.message}`);
      } finally {
        setIsLoadingSummary(false);
      }
    }
    loadTagsSummary();
  }, [date]);

  // Fetch Details when selectedTag or page changes
  const loadTagDetails = useCallback(
    async (pageToLoad = 1) => {
      if (!selectedTag) return;

      setIsLoadingDetails(true);
      setDetailsError(null);
      try {
        const fetchedDetails = await getTagDetails(selectedTag, date, pageToLoad, tagDetails.size);
        setTagDetails(fetchedDetails);
      } catch (err) {
        setDetailsError(err.message);
        toast.error(`Error loading details for ${selectedTag}: ${err.message}`);
      } finally {
        setIsLoadingDetails(false);
      }
    },
    [selectedTag, date, tagDetails.size]
  );

  useEffect(() => {
    if (selectedTag) {
      loadTagDetails(1); // Load first page when tag selection changes
    }
  }, [selectedTag, loadTagDetails]);

  const handleTagClick = (tagName) => {
    if (selectedTag === tagName) {
      setSelectedTag(null); // Deselect if clicked again
      setTagDetails({ items: [], total: 0, page: 1, size: 10, pages: 0 });
    } else {
      setSelectedTag(tagName);
      // Details will be loaded by the useEffect watching selectedTag
    }
  };

  const handleUpdateStatus = async (tagId, statusUpdate, actionName) => {
    // Find the tag to be updated and store its index
    const tagIndex = tagDetails.items.findIndex((item) => item.id === tagId);
    if (tagIndex === -1) return;

    // Create a copy of the current items for optimistic updates
    const updatedItems = [...tagDetails.items];

    // Remove the item immediately (optimistic update)
    updatedItems.splice(tagIndex, 1);

    // Update the UI immediately
    setTagDetails({
      ...tagDetails,
      items: updatedItems,
      total: tagDetails.total - 1,
    });

    try {
      // Make the API call in the background
      const result = await updateTagStatus(tagId, statusUpdate);

      // Show success toast
      toast.success(result.message || `Tag ${actionName}d successfully.`);

      // Update tag summary in the background without waiting
      getTagsSummary(date)
        .then((updatedSummary) => {
          setTagsSummary(updatedSummary);
        })
        .catch((err) => {
          console.error("Error updating summary counts:", err);
        });

      // If current page is empty but there are more pages, load the previous page
      if (updatedItems.length === 0 && tagDetails.page > 1 && tagDetails.pages > 1) {
        loadTagDetails(tagDetails.page - 1);
      }
    } catch (err) {
      // If the API call fails, revert the optimistic update and show error
      toast.error(`Failed to ${actionName} tag: ${err.message}`);

      // Reload the current page data to ensure UI is in sync with server
      loadTagDetails(tagDetails.page);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= tagDetails.pages) {
      loadTagDetails(newPage);
    }
  };

  // Format date for display
  const formatMonthYearForDisplay = (dateStr) => {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    return date.toLocaleString("default", { month: "long", year: "numeric" });
  };

  return (
    <div className="container mx-auto p-4 space-y-6 md:space-y-10">
      <h1 className="text-2xl font-bold mb-6 md:mb-8">Data Quality Tags</h1>

      {/* Filter Section */}
      <div className="p-4 md:p-6 border rounded-md bg-card text-card-foreground shadow-sm mb-4">
        <h2 className="text-lg font-semibold mb-4">Filters</h2>
        <div className="flex gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="date" className="text-sm font-medium">
              Month
            </label>
            <select id="date" className="px-3 py-2 border rounded-md bg-background" value={date} onChange={(e) => setDate(e.target.value)} disabled={isLoadingSummary || isLoadingDetails}>
              <option value={current}>{formatMonthYearForDisplay(current)}</option>
              <option value={previous}>{formatMonthYearForDisplay(previous)}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tags Summary Section */}
      <div className="p-4 md:p-6 border rounded-md bg-card text-card-foreground shadow-sm mb-4">
        <h2 className="text-lg font-semibold mb-4 md:mb-6">Tags Summary</h2>
        {isLoadingSummary && <p>Loading tags summary...</p>}
        {summaryError && <p className="text-red-500">Error loading summary: {summaryError}</p>}
        {!isLoadingSummary && !summaryError && (
          <div className="flex flex-wrap gap-2 md:gap-3">
            {Object.entries(tagsSummary).map(([tagName, count]) => (
              <Badge key={tagName} variant={selectedTag === tagName ? "default" : "secondary"} onClick={() => handleTagClick(tagName)} className="cursor-pointer hover:scale-105 transition-all py-1.5 px-3 text-sm">
                {tagName.replace(/_/g, " ")} ({count})
              </Badge>
            ))}
          </div>
        )}
        {!isLoadingSummary && !summaryError && Object.keys(tagsSummary).length === 0 && <p className="text-muted-foreground">No tags found for {formatMonthYearForDisplay(date)}.</p>}
      </div>

      {/* Listing Table Section */}
      {selectedTag && (
        <div className="p-4 md:p-6 border rounded-md bg-card text-card-foreground shadow-sm min-h-[300px]">
          <h2 className="text-lg font-semibold mb-4">
            Listings for: <span className="font-medium text-primary">{selectedTag.replace(/_/g, " ")}</span>
          </h2>
          {isLoadingDetails && <p>Loading details...</p>}
          {detailsError && <p className="text-red-500">Error loading details: {detailsError}</p>}
          {!isLoadingDetails && !detailsError && (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[20%]">Source</TableHead>
                    <TableHead>Link</TableHead>
                    <TableHead className="text-right w-[180px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tagDetails.items.length > 0 ? (
                    tagDetails.items.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">{item.property.source}</TableCell>
                        <TableCell>
                          <a href={item.property.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline truncate block max-w-xs md:max-w-md lg:max-w-lg">
                            {item.property.url}
                          </a>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex gap-2 justify-end">
                            <Button variant="outline" size="sm" onClick={() => handleUpdateStatus(item.id, { is_solved: true }, "solve")}>
                              Solved
                            </Button>
                            <Button variant="secondary" size="sm" onClick={() => handleUpdateStatus(item.id, { is_ignored: true }, "ignore")}>
                              Ignore
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">
                        No listings found for this tag in {formatMonthYearForDisplay(date)}.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              {/* Pagination Controls */}
              {tagDetails.pages > 1 && (
                <div className="flex items-center justify-between mt-6">
                  <p className="text-sm text-muted-foreground">
                    Page {tagDetails.page} of {tagDetails.pages} (Total: {tagDetails.total} items)
                  </p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handlePageChange(tagDetails.page - 1)} disabled={tagDetails.page <= 1}>
                      Previous
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handlePageChange(tagDetails.page + 1)} disabled={tagDetails.page >= tagDetails.pages}>
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
          {!isLoadingDetails && !detailsError && tagDetails.total === 0 && !selectedTag && <p className="text-muted-foreground">Click a tag above to see related listings.</p>}
        </div>
      )}
    </div>
  );
}
