USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[UsersGroups]    Script Date: 08-03-2026 08:53:55 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[UsersGroups]
(
    [Id] [bigint] IDENTITY(1,1) NOT NULL,
    [Name] [nvarchar](200) NOT NULL,
    [Active] [bit] NOT NULL,
    [Description] [nvarchar](max) NULL,
    [UserGroupTypeId] [bigint] NULL,
    [CustomerId] [bigint] NULL,
    CONSTRAINT [PK_UsersGroups] PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[UsersGroups]  WITH CHECK ADD  CONSTRAINT [FK_UsersGroups_Customers] FOREIGN KEY([CustomerId])
REFERENCES [dbo].[Customers] ([Id])
GO

ALTER TABLE [dbo].[UsersGroups] CHECK CONSTRAINT [FK_UsersGroups_Customers]
GO

ALTER TABLE [dbo].[UsersGroups]  WITH NOCHECK ADD  CONSTRAINT [FK_UsersGroups_UserGroupTypes] FOREIGN KEY([UserGroupTypeId])
REFERENCES [dbo].[UserGroupTypes] ([Id])
GO

ALTER TABLE [dbo].[UsersGroups] NOCHECK CONSTRAINT [FK_UsersGroups_UserGroupTypes]
GO


