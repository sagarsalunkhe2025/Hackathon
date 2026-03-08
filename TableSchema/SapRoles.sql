USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[SapRoles]    Script Date: 08-03-2026 08:49:43 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[SapRoles]
(
    [RoleId] [bigint] IDENTITY(1,1) NOT NULL,
    [RoleName] [nvarchar](400) NULL,
    [SystemId] [bigint] NOT NULL,
    [ContainAllTcodes] [bit] NOT NULL,
    [TotalActivities] [bigint] NULL,
    [RoleTypeId] [bigint] NULL,
    [ParentRole] [nvarchar](400) NULL,
    [MainApplicationArea] [nvarchar](20) NULL,
    [Description] [nvarchar](max) NULL,
    [AuthorizationsHash] [nvarchar](50) NULL,
    [ObjectPath] [nvarchar](300) NULL,
    [LicenseType] [nvarchar](20) NULL,
    [RoleAttribute1] [nvarchar](200) NULL,
    [RoleAttribute2] [nvarchar](200) NULL,
    [RoleAttribute3] [nvarchar](200) NULL,
    [RoleAttribute4] [nvarchar](200) NULL,
    [RoleAttribute5] [nvarchar](200) NULL,
    [RoleAttribute6] [nvarchar](200) NULL,
    [RoleAttribute7] [nvarchar](200) NULL,
    [RoleAttribute8] [nvarchar](200) NULL,
    [RoleAttribute9] [nvarchar](200) NULL,
    [RoleAttribute10] [nvarchar](200) NULL,
    [IsRoleCanBeRemoved] [bit] NULL,
    [IsRoleDeleted] [bit] NOT NULL,
    [MetaDataForRolesId] [bigint] NULL,
    [LastChanged] [datetime] NULL,
    [VirtualRoleAttributes] [nvarchar](max) NULL,
    [IsVirtual] [bit] NOT NULL,
    [RoleScope] [nvarchar](300) NULL,
    CONSTRAINT [PK_SapRoles] PRIMARY KEY CLUSTERED 
(
	[RoleId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[SapRoles] ADD  CONSTRAINT [DF_SapRoles_ContainAllTcodes]  DEFAULT ((0)) FOR [ContainAllTcodes]
GO

ALTER TABLE [dbo].[SapRoles] ADD  CONSTRAINT [DF_SapRoles_IsRoleCanBeRemoved]  DEFAULT ((0)) FOR [IsRoleCanBeRemoved]
GO

ALTER TABLE [dbo].[SapRoles] ADD  CONSTRAINT [DF_SapRoles_IsRoleDeleted]  DEFAULT ((0)) FOR [IsRoleDeleted]
GO

ALTER TABLE [dbo].[SapRoles] ADD  DEFAULT ((0)) FOR [IsVirtual]
GO

ALTER TABLE [dbo].[SapRoles]  WITH CHECK ADD  CONSTRAINT [FK_SapRoles_MetaDataForRoles] FOREIGN KEY([MetaDataForRolesId])
REFERENCES [dbo].[MetaDataForRoles] ([Id])
ON DELETE SET NULL
GO

ALTER TABLE [dbo].[SapRoles] CHECK CONSTRAINT [FK_SapRoles_MetaDataForRoles]
GO

ALTER TABLE [dbo].[SapRoles]  WITH CHECK ADD  CONSTRAINT [FK_SapRoles_RoleTypes] FOREIGN KEY([RoleTypeId])
REFERENCES [dbo].[RoleTypes] ([RoleTypeId])
GO

ALTER TABLE [dbo].[SapRoles] CHECK CONSTRAINT [FK_SapRoles_RoleTypes]
GO

ALTER TABLE [dbo].[SapRoles]  WITH CHECK ADD  CONSTRAINT [FK_SapRoles_Systems] FOREIGN KEY([SystemId])
REFERENCES [dbo].[Systems] ([SystemId])
GO

ALTER TABLE [dbo].[SapRoles] CHECK CONSTRAINT [FK_SapRoles_Systems]
GO


