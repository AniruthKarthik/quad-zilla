-- Database Schema for Supabase Storage and Access Control System
-- Note: auth.users table already exists in Supabase, so we'll reference it

-- Create files table
CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size BIGINT,
    content_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create file_permissions table
CREATE TABLE IF NOT EXISTS file_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    access_level TEXT NOT NULL CHECK (access_level IN ('read', 'write', 'owner')),
    granted_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(file_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_files_user_id ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_created_at ON files(created_at);
CREATE INDEX IF NOT EXISTS idx_file_permissions_file_id ON file_permissions(file_id);
CREATE INDEX IF NOT EXISTS idx_file_permissions_user_id ON file_permissions(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE files ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_permissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for files table
CREATE POLICY "Users can view files they have permission to" ON files
    FOR SELECT USING (
        id IN (
            SELECT file_id FROM file_permissions 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert their own files" ON files
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update files they own" ON files
    FOR UPDATE USING (
        id IN (
            SELECT file_id FROM file_permissions 
            WHERE user_id = auth.uid() AND access_level = 'owner'
        )
    );

CREATE POLICY "Users can delete files they own" ON files
    FOR DELETE USING (
        id IN (
            SELECT file_id FROM file_permissions 
            WHERE user_id = auth.uid() AND access_level = 'owner'
        )
    );

-- RLS Policies for file_permissions table
CREATE POLICY "Users can view permissions for files they have access to" ON file_permissions
    FOR SELECT USING (
        user_id = auth.uid() OR 
        file_id IN (
            SELECT file_id FROM file_permissions 
            WHERE user_id = auth.uid() AND access_level IN ('owner', 'write')
        )
    );

CREATE POLICY "File owners can manage permissions" ON file_permissions
    FOR ALL USING (
        file_id IN (
            SELECT file_id FROM file_permissions 
            WHERE user_id = auth.uid() AND access_level = 'owner'
        )
    );