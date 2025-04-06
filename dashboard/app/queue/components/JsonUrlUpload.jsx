"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload, File, CheckCircle, AlertCircle, Link as LinkIcon } from "lucide-react";

export function JsonUrlUpload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [urlAttribute, setUrlAttribute] = useState("Property Link");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null); // 'success', 'error', or null

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file && file.type === "application/json") {
      setSelectedFile(file);
      setUploadStatus(null);
    } else if (file) {
      alert("Please upload a JSON file");
      event.target.value = null;
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !urlAttribute.trim()) return;

    try {
      setIsUploading(true);

      // Create form data
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/data/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to upload URLs");
      }

      setUploadStatus("success");
    } catch (error) {
      console.error("Error uploading URLs:", error);
      setUploadStatus("error");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Upload URLs</CardTitle>
        <CardDescription>Upload JSON file containing URLs to scrape</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-4">
          <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center hover:bg-muted/50 transition-colors cursor-pointer" onClick={() => document.getElementById("json-upload").click()}>
            <input id="json-upload" type="file" className="hidden" accept=".json" onChange={handleFileChange} />

            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-muted mb-4">
              <Upload className="h-6 w-6 text-muted-foreground" />
            </div>

            {selectedFile ? (
              <div className="flex items-center justify-center gap-2">
                <File className="h-4 w-4" />
                <span className="text-sm font-medium">{selectedFile.name}</span>
              </div>
            ) : (
              <>
                <p className="text-sm font-medium">Upload JSON with URLs</p>
                <p className="text-xs text-muted-foreground mt-1">Only JSON files accepted</p>
              </>
            )}
          </div>
        </div>

        {uploadStatus === "success" && (
          <div className="flex items-center gap-2 text-sm text-green-600 mb-4">
            <CheckCircle className="h-4 w-4" />
            <span>URLs uploaded successfully</span>
          </div>
        )}

        {uploadStatus === "error" && (
          <div className="flex items-center gap-2 text-sm text-red-600 mb-4">
            <AlertCircle className="h-4 w-4" />
            <span>Error uploading URLs</span>
          </div>
        )}

        <Button className="w-full" disabled={!selectedFile || !urlAttribute.trim() || isUploading} onClick={handleUpload}>
          {isUploading ? "Uploading..." : "Upload URLs"}
        </Button>
      </CardContent>
    </Card>
  );
}
