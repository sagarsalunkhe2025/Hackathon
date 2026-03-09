USE [ProfileTailor]
GO

/****** Object:  Table [dbo].[Role_Changes]    Script Date: 09-03-2026 09:20:33 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Role_Changes]
(
    [ChangeId] [bigint] NOT NULL,
    [TransactionCode] [nvarchar](410) NOT NULL,
    [Add] [bit] NOT NULL,
    CONSTRAINT [PK_Role_Changes] PRIMARY KEY CLUSTERED 
(
	[ChangeId] ASC,
	[TransactionCode] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[Role_Changes]  WITH CHECK ADD  CONSTRAINT [FK_Role_Changes_Changes] FOREIGN KEY([ChangeId])
REFERENCES [dbo].[Changes] ([ChangeId])
GO

ALTER TABLE [dbo].[Role_Changes] CHECK CONSTRAINT [FK_Role_Changes_Changes]
GO



