USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[Users]    Script Date: 08-03-2026 08:52:18 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Users]
(
    [UserId] [bigint] IDENTITY(1,1) NOT NULL,
    [SapUserName] [nvarchar](100) NOT NULL,
    [WindowsUserName] [nvarchar](100) NOT NULL,
    [FullName] [nvarchar](200) NULL,
    [EMail] [varchar](max) NULL,
    [MainApplicationArea] [varchar](20) NULL,
    [SecendApplicationArea] [varchar](20) NULL,
    [UserType] [bigint] NULL,
    [CreateDate] [datetime] NULL,
    [InvalidDate] [datetime] NULL,
    [SapUserType] [varchar](2) NULL,
    [UserGroup] [varchar](max) NULL,
    [IncorrectLogons] [int] NULL,
    [LockStatus] [int] NULL,
    [LastLogon] [datetime] NULL,
    [PasswordChangedDate] [datetime] NULL,
    [UserComputer] [varchar](50) NULL,
    [EndLearningPhase] [datetime] NULL,
    [IsDeleted] [bit] NULL,
    [SystemId] [bigint] NOT NULL,
    [Department] [nvarchar](50) NULL,
    [City] [nvarchar](100) NULL,
    [CountryISO] [nvarchar](4) NULL,
    [TimeZone] [nvarchar](50) NULL,
    [RfcUserComputer] [varchar](50) NULL,
    [CompanyName] [nvarchar](200) NULL,
    [CreatedOn] [datetime] NULL,
    [DeletedOn] [datetime] NULL,
    [EmployeeNumber] [nvarchar](100) NULL,
    [UnsecureCommunicationPermitted] [bit] NOT NULL,
    [DeactivatePassword] [bit] NOT NULL,
    [ChangedBy] [nvarchar](50) NULL,
    [LastChange] [datetime] NULL,
    [Building] [nvarchar](200) NULL,
    [IsEmployeeNumberManual] [bit] NULL,
    [CreatedBy] [nvarchar](50) NULL,
    [CustomerId] [bigint] NOT NULL,
    [ExtraValues] [nvarchar](max) NULL,
    [LicenseType] [nvarchar](20) NULL,
    [ValidFrom] [datetime] NULL,
    [UserHash] [int] NULL,
    [LastSyncTimestampUTC] [datetime] NULL,
    CONSTRAINT [PK_Users] PRIMARY KEY CLUSTERED 
(
	[UserId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO

ALTER TABLE [dbo].[Users] ADD  CONSTRAINT [DF_Users_IsDeleted]  DEFAULT ((0)) FOR [IsDeleted]
GO

ALTER TABLE [dbo].[Users] ADD  CONSTRAINT [DF_Users_UnsecureCommunicationPermitted]  DEFAULT ((0)) FOR [UnsecureCommunicationPermitted]
GO

ALTER TABLE [dbo].[Users] ADD  CONSTRAINT [DF_Users_DeactivatePassword]  DEFAULT ((0)) FOR [DeactivatePassword]
GO

ALTER TABLE [dbo].[Users] ADD  CONSTRAINT [DF_Users_IsEmployeeNumberManual]  DEFAULT ((0)) FOR [IsEmployeeNumberManual]
GO

ALTER TABLE [dbo].[Users]  WITH NOCHECK ADD  CONSTRAINT [FK_Users_Customers] FOREIGN KEY([CustomerId])
REFERENCES [dbo].[Customers] ([Id])
GO

ALTER TABLE [dbo].[Users] CHECK CONSTRAINT [FK_Users_Customers]
GO

ALTER TABLE [dbo].[Users]  WITH NOCHECK ADD  CONSTRAINT [FK_Users_Systems] FOREIGN KEY([SystemId])
REFERENCES [dbo].[Systems] ([SystemId])
GO

ALTER TABLE [dbo].[Users] CHECK CONSTRAINT [FK_Users_Systems]
GO

ALTER TABLE [dbo].[Users]  WITH NOCHECK ADD  CONSTRAINT [FK_Users_UserTypes] FOREIGN KEY([UserType])
REFERENCES [dbo].[UserTypes] ([UserTypeId])
GO

ALTER TABLE [dbo].[Users] CHECK CONSTRAINT [FK_Users_UserTypes]
GO


