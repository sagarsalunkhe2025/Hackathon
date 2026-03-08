USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[RoleTypes]    Script Date: 08-03-2026 08:53:27 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[RoleTypes]
(
    [RoleTypeId] [bigint] IDENTITY(1,1) NOT NULL,
    [Description] [nvarchar](200) NOT NULL,
    [IconPath] [nvarchar](200) NOT NULL,
    [IsActive] [bit] NOT NULL,
    [MaxNumberOfInstancesForUser] [bigint] NULL,
    CONSTRAINT [PK_RoleTypes] PRIMARY KEY CLUSTERED 
(
	[RoleTypeId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[RoleTypes] ADD  DEFAULT ((1)) FOR [IsActive]
GO


