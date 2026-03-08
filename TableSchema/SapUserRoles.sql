USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[SapUserRoles]    Script Date: 08-03-2026 08:49:51 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[SapUserRoles]
(
    [UserId] [bigint] NOT NULL,
    [RoleName] [nvarchar](400) NOT NULL,
    [IsRoleFromCompositeRole] [bit] NOT NULL,
    [AssignmentDate] [datetime] NULL,
    [AssignmentBy] [nvarchar](50) NULL,
    [RoleUntilDate] [datetime] NULL,
    CONSTRAINT [PK_SapUserRoles] PRIMARY KEY CLUSTERED 
(
	[UserId] ASC,
	[RoleName] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[SapUserRoles] ADD  CONSTRAINT [DF_SapUserRoles_IsRoleFromCompositeRole]  DEFAULT ((0)) FOR [IsRoleFromCompositeRole]
GO

ALTER TABLE [dbo].[SapUserRoles]  WITH NOCHECK ADD  CONSTRAINT [FK_SapUserRoles_Users] FOREIGN KEY([UserId])
REFERENCES [dbo].[Users] ([UserId])
ON DELETE CASCADE
GO

ALTER TABLE [dbo].[SapUserRoles] CHECK CONSTRAINT [FK_SapUserRoles_Users]
GO


